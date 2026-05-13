# benchmark — 축구 정보 사이트 (방송용 페이지 포함)

## 1. 프로젝트 개요

축구 정보를 제공하는 웹사이트. 일부 페이지는 **방송용** 으로 디자인되어 방송 소프트웨어가 크로마키로 합성해 송출하는 용도로 사용된다.
데이터 소스는 API-Football(Ultra plan), DB는 Supabase, 캐시/세션 보조는 Upstash, 백엔드는 FastAPI + SQLAlchemy.

## 2. 대상 리그 (5개, 고정)

- Premier League
- UEFA Champions League
- UEFA Europa League
- Carabao Cup (EFL Cup)
- FA Cup

## 3. 데이터 정책

- **보관 범위**: 최신 2시즌 (현재 시즌 + 직전 시즌)
- **컵 대회 fixture**: 시즌 전체. 추첨 미정 라운드는 빈 슬롯으로 두고 6시간 sync 시 채움
- **외부 ID upsert**: API-Football 의 `fixture_id`, `team_id`, `player_id`, `league_id` 를 unique key 로 upsert

## 4. 워커 (2종)

워커는 API-Football → DB 적재 전담. API endpoint 와 분리된 독립 기능.

| 워커 | 주기 | 책임 |
|---|---|---|
| `daily-sync` | KST 00/06/12/18 (4회/일) | 5개 리그의 fixtures, fixture 상세, league/team/player 메타 적재 |
| `translation-filler` | 1분 간격 상시 (큐 비면 즉시 종료) | 번역 테이블에서 `name_ko IS NULL` row 탐지 → OpenAI 호출 → 채움 |

방송용 페이지의 라이브 데이터는 **워커가 아니라 API endpoint + 캐시** 로 처리한다 (스트리머가 방송용 페이지를 활용할 때만 호출). 워커 영역과 분리.

운영 원칙:
- **API-Football rate limit (Ultra plan)**: 450 req/min ≈ 7.5 RPS. 동시 호출 semaphore 상한 = **6** (안전 마진 포함)
- **재시도**: API 실패는 지수 백오프, 한 사이클 내 최대 3회. 그 이상은 다음 주기로 이월
- **멱등성**: 외부 ID 기반 upsert. 부분 적재 후 재시작 안전
- **단일 인스턴스 전제**: Koyeb 단일 service 이므로 분산 락 불필요. APScheduler in-process 단일 스케줄러로 충분
- **수동 트리거**: 각 워커는 ADMIN role 전용 admin endpoint 로 수동 실행 가능

## 5. 번역 테이블

영문/원본 데이터는 entity 테이블 (`league`, `team`, `player`) 에서 관리. 번역 테이블은 **한글 표기만** 별도로 관리한다.

### 5.1 테이블 구성 (3개 분리)

| 테이블 | 컬럼 (개념) |
|---|---|
| `league_translation` | `league_id` (FK), `name_ko`, `short_name_ko`, `source`, `verified`, `updated_at` |
| `team_translation` | `team_id` (FK), `name_ko`, `short_name_ko`, `source`, `verified`, `updated_at` |
| `player_translation` | `player_id` (FK), `name_ko`, `short_name_ko`, `source`, `verified`, `updated_at` |

- 분리 이유: 각 entity 별 FK 로 참조 무결성 확보, ORM 모델 명확
- `name_ko` / `short_name_ko` 가 NULL 인 동안 API 응답은 entity 테이블의 영문 이름 그대로 fallback
- MVP 에서는 자동번역 결과를 그대로 노출. 검수 큐(ADMIN 가 의심 번역 수정)는 MVP 미포함

### 5.2 적재 책임 분담

| 동작 | 주체 | 방식 |
|---|---|---|
| entity 테이블 (league/team/player) 적재 | `daily-sync` | upsert (전체 덮어쓰기) |
| 번역 테이블에 row 보장 (새 entity 발견 시) | `daily-sync` | INSERT (외부 ID unique 충돌 시 무시). 한글 컬럼은 NULL. **기존 row 절대 갱신 안 함** |
| 번역 테이블의 한글 컬럼 채움 | `translation-filler` | `name_ko IS NULL` row 탐지 → OpenAI 호출 → UPDATE |

이 분담으로 daily-sync 의 "전체 덮어쓰기" 가 번역 테이블의 기존 한글값에 영향을 주지 않는다.

### 5.3 시드 데이터

| 대상 | 출처 | 방식 |
|---|---|---|
| **player_translation** | 이전 프로젝트 산출물 `_Player__202605131748.csv` (6,422 row) | gpt-3.5-turbo few-shot 자동번역 + 주요 선수 수동 수정. `source='gpt-3.5-fewshot-curated'` |
| **team_translation** | 이 세션에서 사용자가 5 리그 대상 팀 번역 진행 | 시드 CSV 생성 |
| **league_translation** | 이 세션에서 사용자가 5 리그 한글표기 결정 | 시드 CSV 생성 |

### 5.4 운영 중 자동번역 (`translation-filler`)

- 대상: 시드에 없는 신규 entity (신규 선수, 신규 컵대회 참가팀 등) — daily-sync 가 만든 NULL row
- 모델: **`gpt-3.5-turbo` + few-shot prompting** (음역 중심, web_search 사용 안 함)
   - 이유: 시드 CSV 와 같은 방식이라 표기 일관성 유지, 비용이 web_search 방식 대비 ~1/100
   - 한계: 한국 매체 통용 표기 검증 불가. 마이너 entity 는 단순 음역. MVP 허용 범위
- few-shot 예시: 시드 CSV 에서 무작위 추출하여 일관성 강화
- 1분 폴링, `name_ko IS NULL` row 가 있을 때만 호출 (없으면 즉시 종료)
- 비용: 신규 entity 등장 빈도 낮아 월 부담 무시 가능

## 6. 데이터 신선도 SLA

| Endpoint 종류 | 신선도 보장 | 처리 방식 |
|---|---|---|
| 일반 사용자용 (일정, 결과, 통계, 팀/선수 메타) | 6시간 이내 | daily-sync 가 적재한 DB 조회 |
| 방송용 페이지 라이브 데이터 | 실시간 | 스트리머 호출 시점에 API endpoint 가 API-Football 호출 (캐시 TTL 단기) |
| 번역명 | best-effort | 누락 시 영문 fallback |

## 7. 인증/권한

### Role (DB에 저장)
- `USER` — 일반 사이트 열람
- `STREAMER` — 방송용 페이지 사용 가능
- `ADMIN` — 운영/검수 권한

### 세션
- JWT (access) — stateless, 짧은 만료
- Refresh token rotation/blacklist 는 **Upstash** 에 저장
- Upstash 는 MVP 에서 **refresh token rotation/blacklist 용도로만** 사용. 응답 캐시 확장은 post-MVP

### 방송용 페이지 인증
- 방송용 페이지는 일반 웹사이트의 한 라우트로 제공되며, 방송 SW 가 해당 페이지를 캡처해 크로마키 합성한다 (OBS 브라우저 소스 임베드 아님)
- 따라서 인증은 일반 웹앱과 동일: STREAMER role JWT
- 방송용 페이지 배경 크로마키 키컬러: **OBS 기본 녹색** (`#00B140`, chroma green)

## 8. 개발 프로세스

**프론트엔드 follow 방식** — 백엔드는 프론트가 정의한 엔드포인트 목록을 받아 구현한다.

1. 프론트엔드가 화면/기능을 mockup 으로 구현
2. mockup 데이터를 가져올 **endpoint 목록 작성** (path, method, 응답 shape 초안)
3. 백엔드는 그 목록을 기준으로:
   - 요구 데이터 정의
   - 필요한 DB 컬럼/관계 점검 (없으면 추가)
   - API 구현
4. 프론트가 mock 을 실 endpoint 로 교체

이 순서를 거꾸로 가지 않는다. 백엔드가 "필요할 것 같은" API 를 선제 구현하지 않는다.

## 9. 기술 스택

| 영역 | 도구 |
|---|---|
| 백엔드 프레임워크 | FastAPI |
| ORM | SQLAlchemy |
| DB | Supabase (Postgres) — supabase CLI 로 마이그레이션/조작 |
| 캐시/세션 보조 | Upstash (Redis) — upstash CLI |
| 외부 데이터 | API-Football (Ultra plan), API-Football MCP 활용 |
| 자동번역 | OpenAI API |

## 10. CLI / MCP 활용 규칙

- DB 스키마 변경: supabase CLI 마이그레이션 파일로 관리. SQLAlchemy 모델과 마이그레이션은 항상 동기 상태 유지
- API-Football 응답 구조 확인: 코드 작성 전 **API-Football MCP** 로 실응답 조회 후 모델 정의
- Upstash 키 설계: 코드 푸시 전 upstash CLI 로 키 패턴/TTL 검증

## 11. 향후(post-MVP) 검토 항목

- Upstash 를 API-Football / OpenAI 응답 캐시로 확장 (MVP 외)
- 자동번역 검수 큐 + ADMIN 검수 UI (MVP 외)
- 번역 정밀도 업그레이드: `gpt-4.1` + Responses API `web_search` + `filters.allowed_domains`(ko.wikipedia.org, 한국 스포츠 미디어). 음역 한계가 운영상 문제될 때 도입. PoC 스크립트는 `scripts/translate_poc.py` 에 보존
- 방송용 라이브 endpoint 의 캐시 TTL 튜닝 (방송용 페이지 UX 보고 결정)
- API-Football semaphore 상한 튜닝 (현재 6, 실측 후 조정)
- 다중 인스턴스 스케일 도입 시 워커 분산 락 (Upstash `SET NX`) 추가 필요

## 12. Harness 운영

- 계획: Plans.md (v2 포맷, Task/내용/DoD/Depends/Status)
- 실행: `/harness-work` 계열
- 동기화: `/harness-sync`
- 본 CLAUDE.md 는 도메인/규칙의 SSOT. 변경 시 PR 또는 명시적 결정 기록 동반
