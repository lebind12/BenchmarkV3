---
worker_id: daily-sync
title: API-Football → DB 정기 적재 워커
created: 2026-05-13
priority: MVP
status: requirements-only
---

## 1. 목적

API-Football 의 5리그 데이터를 6시간 주기로 Supabase DB 에 적재한다. 일반 사용자 화면이 제공하는 모든 비실시간 데이터(경기 일정/결과, 팀/선수 메타, 순위표 등) 의 정본을 만든다.

## 2. 스케줄

- 종류: cron
- 주기: **KST 매일 00:00, 06:00, 12:00, 18:00** (4회/일)
- 시작 조건: 직전 사이클이 종료 상태일 때만 (in-process scheduler 가 자연스럽게 보장)
- 정지 조건: 컨테이너 종료 신호 받으면 진행 중 step 완료 후 종료 (graceful)

## 3. 트리거 / 입력

### 데이터 소스
- API-Football v3 (Ultra plan)
- endpoints 사용:
  - `GET /leagues?id={id}`
  - `GET /teams?league={id}&season={year}`
  - `GET /fixtures?league={id}&season={year}`
  - `GET /fixtures/events?fixture={id}`
  - `GET /fixtures/statistics?fixture={id}`
  - `GET /fixtures/lineups?fixture={id}`
  - `GET /players?team={id}&season={year}`
  - `GET /standings?league={id}&season={year}`

### 입력 파라미터
- 화이트리스트: 5리그 external_id `[39, 2, 3, 48, 45]`
- 시즌: `current_season` (league 테이블의 `current_season` 컬럼) + `current_season - 1`

## 4. 처리 단계

```
[사이클 시작]
   ↓
Step 1. 리그 메타 sync (5 calls)
   ↓
Step 2. 5리그 × current_season 팀 목록 sync (5 calls)
   ↓
Step 3. 5리그 × {current, previous} fixture 목록 sync (10 calls)
   ↓
Step 4. 활성 fixture 큐(B) 산정 (DB 쿼리만, API 호출 없음)
   ↓
Step 5. 활성 fixture 의 fixture_detail sync (events/statistics/lineups, 각 3 calls)
   ↓
Step 6. 활성 팀의 선수 sync (team batch, /players?team=X&season=Y)
   ↓
Step 7. standings sync (5리그 × current_season, 5 calls)
   ↓
Step 8. team_season 정션 upsert (DB-only)
   ↓
Step 9. *_translation 신규 row 보장 (DB-only)
   ↓
[사이클 종료]
```

### Step 별 상세

#### Step 1. 리그 메타
- 5개 external_id 각각 `GET /leagues?id={external_id}`
- 응답 매핑:
  - `league.id` → `external_id`
  - `league.name` → `name`
  - `league.type` → `type`
  - `league.logo` → `logo_url`
  - `country.{name, code, flag}` → `country_name`, `country_code`, `country_flag`
  - `seasons[]` 중 `current=true` 인 row 의 `year` → `current_season`
- upsert (외부 ID 기반 전체 덮어쓰기)

#### Step 2. 팀 목록 (current_season 만)
- 5리그 각각 `GET /teams?league={external_id}&season={current_season}`
- 응답의 각 entry 마다:
  - `venue` 객체 → venue 테이블 upsert (`external_id` 기반)
  - `team` 객체 → team 테이블 upsert (`external_id` 기반, `venue_id` 는 위에서 얻은 내부 ID)
  - slug 자동 생성: `lower(slugify(team.name)) + '-' + team.external_id`

#### Step 3. fixture 목록
- 5리그 × 2시즌 각각 `GET /fixtures?league={external_id}&season={year}`
- 응답의 각 fixture 마다 fixture 테이블 upsert:
  - status / score / kickoff_at / venue / home_team / away_team 모두 전체 덮어쓰기
  - 컵 추첨 미정 라운드 → `home_team_id` / `away_team_id` = NULL (API 응답에서 teams.home.id / teams.away.id 가 null/0 일 때)
  - 새 team / venue 가 fixture 응답에 있고 DB 에 없으면 → 본 step 에선 fixture 만 처리하고 team/venue 는 step 2 / step 6 에서 처리. fixture 의 FK 가 일시적으로 NULL 일 수 있음

#### Step 4. 활성 fixture 큐(B) 산정
DB 쿼리만:
```sql
SELECT id FROM fixture
WHERE league_id IN (5리그 내부 id)
  AND season_year IN (current_season, current_season - 1)
  AND (
       status_short NOT IN ('FT', 'AET', 'PEN', 'CANC', 'PST')      -- 미종료
    OR (status_short IN ('FT', 'AET', 'PEN')
        AND kickoff_at > now() - INTERVAL '48 hours')               -- 종료 후 48h
    OR (kickoff_at > now()
        AND kickoff_at < now() + INTERVAL '14 days')                -- 다가오는 14일
  );
```
- 결과를 메모리에 보관하고 Step 5, 6 가 사용

#### Step 5. fixture_detail
- 활성 fixture 각각:
  - `GET /fixtures/events?fixture={external_id}`
  - `GET /fixtures/statistics?fixture={external_id}`
  - `GET /fixtures/lineups?fixture={external_id}`
- 3 응답 묶어 fixture_detail upsert:
  - `events` = events 응답 JSONB
  - `statistics` = statistics 응답 JSONB
  - `lineups` = lineups 응답 JSONB
  - `fetched_at` = now()

#### Step 6. 활성 팀의 선수
- Step 4 의 활성 fixture 의 `home_team_id` / `away_team_id` 집합 (DISTINCT, NULL 제외)
- 각 활성 팀 × current_season 으로 `GET /players?team={external_id}&season={current_season}` (페이지네이션 응답 처리)
- 응답의 각 entry 마다:
  - `player` 객체 → player 테이블 upsert (전체 덮어쓰기)
    - `height` / `weight` 문자열 → 정수 파싱 (`'188 cm'` → 188)
    - `current_team_id` = 호출한 team 의 내부 id
  - `statistics[]` 배열 → player_season_stat upsert (각 entry 가 player × team × league × season 단위)
    - 핵심 컬럼 추출 (position, shirt_number, appearances, minutes, rating, goals, assists, yellow_cards, red_cards)
    - 전체 stats object → `raw_stats` JSONB

#### Step 7. standings
- 5리그 × current_season 각각 `GET /standings?league={external_id}&season={current_season}`
- 응답의 각 team standing row → standings 테이블 upsert
- `group_name` 은 API 응답의 group 이름 (UCL/UEL group stage). 리그면 NULL

#### Step 8. team_season 정션 upsert
- Step 3 에서 적재한 모든 fixture 의 (league_id, season_year, home_team_id ∪ away_team_id) 추출
- 각 (team_id, league_id, season_year) → `INSERT INTO team_season ... ON CONFLICT DO NOTHING`

#### Step 9. 번역 테이블 row 보장
- Step 1, 2, 6 에서 새로 만들어진 league / team / player id 각각:
  - `INSERT INTO league_translation (league_id) VALUES (...) ON CONFLICT (league_id) DO NOTHING`
  - `INSERT INTO team_translation (team_id) VALUES (...) ON CONFLICT (team_id) DO NOTHING`
  - `INSERT INTO player_translation (player_id) VALUES (...) ON CONFLICT (player_id) DO NOTHING`
- 한글 컬럼은 NULL → translation-filler 워커가 채움
- 기존 row 는 절대 건드리지 않음 (한글값 보호)

## 5. 출력 / 부수 효과

### 갱신 테이블
| 테이블 | 동작 |
|---|---|
| `league` | 전체 덮어쓰기 upsert (5 row) |
| `venue` | 전체 덮어쓰기 upsert (활성 팀의 홈 venue + fixture venue) |
| `team` | 전체 덮어쓰기 upsert (5리그 current_season 의 모든 팀) |
| `fixture` | 전체 덮어쓰기 upsert (5리그 × 2시즌의 모든 fixture) |
| `fixture_detail` | 전체 덮어쓰기 upsert (활성 fixture 만) |
| `player` | 전체 덮어쓰기 upsert (활성 팀의 선수) |
| `player_season_stat` | upsert (활성 player × team × league × season) |
| `standings` | 전체 덮어쓰기 upsert (5리그 × current_season) |
| `team_season` | INSERT ON CONFLICT DO NOTHING (정션 row 보장) |
| `*_translation` | INSERT ON CONFLICT DO NOTHING (신규만, 한글 NULL) |

### 외부 부수 효과
- 없음 (Upstash / OpenAI / 외부 알림 없음)

## 6. 멱등성 / 재시도

### 멱등성
- 모든 entity 테이블은 `external_id` 기반 upsert (전체 덮어쓰기) → 같은 사이클 두 번 실행해도 결과 동일
- 번역 테이블은 INSERT ON CONFLICT DO NOTHING → 두 번 실행해도 기존 한글 보호
- 부분 실패 후 다음 사이클 자연 회복 (외부 ID 기반)

### 재시도 정책
- 각 API 호출: 지수 백오프 (1s → 2s → 4s) 최대 3회. 그 이상 실패는 다음 사이클로 이월
- step 단위로 실패해도 다음 step 진행 (전체 사이클 중단 X)
- **fatal 조건** (전체 사이클 중단):
  - API 인증 실패 (401)
  - DB 접속 불가
  - 위 두 경우만 사이클 abort + 운영자 알림

## 7. 분산 락

- **사용 안 함** (CLAUDE.md §4 단일 인스턴스 전제)
- APScheduler in-process 단일 스케줄러로 중복 실행 자연 차단
- 다중 인스턴스 도입 시 Upstash `SET NX` 추가 필요 (post-MVP)

## 8. 동시성 / 외부 API 제약

| 항목 | 값 |
|---|---|
| API-Football rate limit | 450 req/min (Ultra plan) |
| 동시 호출 semaphore | 6 |
| 한 사이클 평균 호출 수 | 205~375 |
| 한 사이클 예상 소요 시간 | 1~3분 (semaphore 6 + 평균 0.5s/call) |

## 9. 오류 처리

| 분류 | 처리 |
|---|---|
| network timeout | 지수 백오프 3회 |
| 4xx (요청 오류, 404 포함) | 해당 row skip, 로그 기록, 다음 step 진행 |
| 401 (인증 실패) | 사이클 abort + 운영자 알림 |
| 429 (rate limit 초과) | 지수 백오프 3회 (semaphore 가 일반적으로 차단) |
| 5xx (서버 오류) | 지수 백오프 3회 |
| DB 트랜잭션 실패 | 해당 row skip, 로그 기록 |
| DB 접속 불가 | 사이클 abort + 운영자 알림 |
| 응답 파싱 오류 | 해당 entity skip, 로그 기록 |

## 10. 모니터링 / 로깅

매 사이클 종료 시 다음 메트릭을 stdout 으로:
- `cycle_started_at`, `cycle_ended_at`, `duration_seconds`
- `api_calls_total`, `api_calls_failed`
- `entities_upserted`: `{league: N, team: N, fixture: N, fixture_detail: N, player: N, player_season_stat: N, standings: N}`
- `translation_rows_created`: `{league: N, team: N, player: N}`
- `errors`: 오류 분류별 카운트

알람 조건 (운영자 통보):
- 연속 3 사이클 실패
- API 인증 오류 발생
- DB 접속 불가
- 사이클 소요 시간 > 30분 (비정상)

알람 채널: MVP 단계 → 일단 stdout 로깅만. 추후 결정.

## 11. 의존성

### DB 테이블 (읽기)
- league (current_season 조회)
- fixture (Step 4 활성 큐 산정용)
- player (current_team_id 조회)

### DB 테이블 (쓰기)
- 위 §5 의 모든 테이블

### 외부 API
- API-Football v3 (Ultra plan)

### 선행 작업
- league 5 row 시드 (사용자가 5리그 한글표기 작성 후 시드 import) — 본 워커 시작 전 필수
- Supabase 프로젝트 + 마이그레이션 적용 (Phase 1 완료)
- API-Football API key 환경변수 설정

### 후속 워커
- translation-filler 가 본 워커가 만든 NULL 한글 row 들을 채움

## 12. 비기능

| 항목 | 값 |
|---|---|
| 1 사이클 평균 시간 | 1~3분 |
| 사이클 당 API 호출 | 205~375 |
| 일일 API 호출 | 820~1,500 (Ultra 한도 75,000 의 1~2%) |
| 메모리 사용 | 활성 fixture 수 × 평균 50KB JSON ≈ 5~10MB 피크 |
| CPU 사용 | 낮음 (I/O 바운드) |
| DB 트랜잭션 수 | 사이클 당 수백 |

## 13. 테스트 전략

### 단위 테스트
- 각 step 의 응답 파싱 로직 (API-Football 고정 fixture JSON 사용)
- height/weight 문자열 → 정수 파싱
- 활성 fixture 쿼리 SQL 생성 (시간 임계치 등)
- upsert SQL 생성 (전체 덮어쓰기 vs INSERT ON CONFLICT DO NOTHING)

### 통합 테스트
- 격리 schema 사용
- 고정 fixture JSON 으로 mock API → 사이클 1회 실행 → DB 상태 검증
- 멱등성: 같은 mock 응답으로 2회 실행 → DB 상태 동일
- 부분 실패 회복: Step 5 에서 일부 fixture detail mock 실패 → 다음 사이클에서 재시도 동작 확인
- 컵 추첨 미정 라운드 처리 (home/away NULL)

### 회귀 / 멱등성 테스트
- 동일 mock 응답 2회 적용 → row count 변화 없음
- 외부 ID 충돌 시 기존 데이터 보존 (특히 번역 테이블의 한글 NULL → 값 → NULL 변화 금지)

## 14. BE 팀이 결정해도 되는 것

- 내부 함수 / 모듈 구조 (app/workers/daily_sync/ 안에서 자유)
- DB 쿼리 최적화 방식
- 응답 파싱 헬퍼 구조
- 단위 테스트 케이스 세부

## 15. BE 팀이 결정해서는 안 되는 것 (메인 확인 필요)

- 스케줄 주기 변경 (KST 00/06/12/18 → 다른 시각)
- 활성 fixture 임계치 (48h, 14d) 변경
- 적재 정책 변경 (전체 덮어쓰기 vs delta)
- 외부 API 호출 횟수 / 동시성 상한 (semaphore 6) 변경
- 새 endpoint / 새 테이블 추가
- DB 스키마 변경 (별도 Phase 1 task)
- 알람 채널 선택

## 16. 미확정 / 메모

- 알람 채널 (Slack / email / 로그만): 미정. 운영 후 결정
- 컵 추첨 미정 라운드의 빈 슬롯 의도: API 응답에서 home/away 가 null/0 일 때 NULL 로 저장. 추첨 결과 나오면 다음 사이클에서 채워짐
- 시즌 전환 (예: EPL 8월 새 시즌 시작): API 의 seasons[] 의 current=true 가 자동으로 새 year 가리킴. Step 1 에서 자연스럽게 반영됨. 이때 옛 시즌의 직전 시즌 = 변경 X
- 최신 2시즌 보관 정책: 사이클 종료 후 별도 cleanup step 없이, 어차피 daily-sync 는 최신 2시즌만 sync 함. 더 오래된 row 가 DB 에 있어도 본 워커가 관여 안 함 (필요 시 별도 cleanup 워커 또는 운영 SQL)
