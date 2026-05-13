# Phase 4 / W2 — daily-sync 워커

본 문서는 BE 워크플로 spec 산출물이며, **endpoint 가 아닌 백그라운드 워커** 의 요구사항 mirror 다.
정본은 `docs/workers/daily-sync.md` (16 섹션 / 9 step). 본 문서는 SSOT 를 BE 팀 implementation/testing 관점으로 재정리.

> ⚠️ **불변 원칙** (dev 가 위반하면 reviewer REQUEST_CHANGES)
> - 스케줄 = **KST 00 / 06 / 12 / 18 cron** 고정
> - 활성 fixture 임계치 = **종료 후 48h** / **다가오는 14d** 고정
> - 적재 정책 = entity 테이블 **전체 덮어쓰기 upsert**, 정션/번역 = **INSERT ON CONFLICT DO NOTHING**
> - 동시 호출 semaphore = **6** 고정 (API-Football Ultra 7.5 RPS 안전 마진)
> - 대상 league = `WHERE is_active = true` (L1 으로 추가된 컬럼). 5리그 + 추후 ADMIN 추가
> - 대상 시즌 = 각 league `current_season` + `current_season - 1` (2시즌)
> - league 처리는 5리그 / 컵 추첨 미정 home/away NULL 허용
> - fatal abort 조건: **401, DB 접속 불가 두 가지뿐** (그 외는 row skip + 다음 사이클 재시도)

## 1. 스코프 / 디렉토리

- 워커 모듈 (be-dev 영역): `app/workers/daily_sync/` (모듈 분할은 dev 자유)
- 엔트리: 사이클 1회 실행 함수 (예: `daily_sync.runner.run_cycle(session, api_client)`) + APScheduler cron 등록 함수
- 본 spec 단계 be-test 는 `docs/` + `tests/` + `tests/fixtures/api_football/` 만 수정

## 2. 입력

- DB: `SELECT * FROM league WHERE is_active = true` (동적 조회)
- 시즌: 각 league row 의 `current_season` 컬럼, 그리고 `current_season - 1`
- API-Football v3 (Ultra plan), 환경변수 `API_FOOTBALL_KEY`

## 3. 처리 단계 (Step 1 ~ 9)

| Step | 동작 | API calls | DB |
|---|---|---|---|
| 1 | 활성 league 메타 sync | `GET /leagues?id={external_id}` × N (활성 리그 수) | `league` upsert |
| 2 | 5리그 × current_season 팀 + venue | `GET /teams?league=&season=` × N | `team`, `venue` upsert |
| 3 | 5리그 × 2시즌 fixture 목록 | `GET /fixtures?league=&season=` × 2N | `fixture` upsert (home/away NULL 허용) |
| 4 | 활성 fixture 큐(B) 산정 | (DB 쿼리, API 0회) | SELECT |
| 5 | 활성 fixture 의 detail | `GET /fixtures/events,statistics,lineups?fixture=` × 3 × `len(queue B)` | `fixture_detail` upsert |
| 6 | 활성 팀의 선수 | `GET /players?team=&season=` × len(DISTINCT 활성 team) | `player`, `player_season_stat` upsert |
| 7 | standings | `GET /standings?league=&season=` × N | `standings` upsert |
| 8 | team_season 정션 upsert | (DB-only) | `team_season` INSERT ON CONFLICT DO NOTHING |
| 9 | 번역 테이블 row 보장 | (DB-only) | `*_translation` INSERT ON CONFLICT DO NOTHING (한글 NULL) |

### Step 3 — 컵 추첨 미정 라운드

API 응답에서 `teams.home.id` / `teams.away.id` 가 null/0 일 때 `fixture.home_team_id` / `fixture.away_team_id` = NULL 로 INSERT. db-schema.md §5 의 NULL 정책 사용.

### Step 4 — 활성 fixture 큐 SQL

```sql
SELECT id, external_id FROM fixture
WHERE league_id IN (활성 리그 내부 id)
  AND season_year IN (current_season, current_season - 1)
  AND (
       status_short NOT IN ('FT', 'AET', 'PEN', 'CANC', 'PST')
    OR (status_short IN ('FT', 'AET', 'PEN') AND kickoff_at > now() - INTERVAL '48 hours')
    OR (kickoff_at > now() AND kickoff_at < now() + INTERVAL '14 days')
  );
```

### Step 6 — height / weight 파싱
- `'188 cm'` → `188` (smallint)
- `'78 kg'` → `78` (smallint)
- 파싱 실패 시 NULL (raise 금지)
- API typo `appearences` → `appearances` 컬럼

### Step 9 — 번역 테이블 보호
- INSERT ON CONFLICT (entity_id) DO **NOTHING**
- 기존 row 절대 갱신 안 함 (한글 컬럼 보호)

## 4. 멱등성

- 모든 entity 테이블: `external_id` 기반 upsert (전체 덮어쓰기) — 같은 응답 2회 적용해도 결과 동일
- 정션 / 번역: INSERT ON CONFLICT DO NOTHING — 두 번 적용해도 row 증가 없음
- 부분 실패 후 다음 사이클 자연 회복

## 5. 재시도 / 백오프

- 각 API 호출 1s/2s/4s × 3회 지수 백오프
- step 단위 부분 실패 → 다음 step 진행 (사이클 전체 중단 X)
- **fatal abort**: API 401 / DB 접속 불가 만

## 6. 동시성

- semaphore **6**
- 분산 락 없음 (단일 인스턴스 전제)

## 7. 의존성 / 선행

- L1 (`league.is_active`) 머지 완료 (전제)
- Phase 1 13 테이블 + 마이그레이션 적용
- league 5 row 시드 (사용자 작성 후 import)
- `API_FOOTBALL_KEY` 환경변수

## 8. 오류 처리 매트릭스

| 분류 | 처리 |
|---|---|
| network timeout / 5xx | 1s/2s/4s × 3회 백오프, 그래도 실패 시 row skip |
| 4xx (404 등) | 해당 row skip + 로그, 다음 step 진행 |
| 401 인증 실패 | **fatal abort** + 알람 |
| 429 rate limit | 백오프 3회 (semaphore 가 일반적으로 차단) |
| DB 트랜잭션 실패 | row skip + 로그 |
| DB 접속 불가 | **fatal abort** + 알람 |
| JSON 파싱 실패 | entity skip + 로그 |

## 9. 로깅 / 알람

사이클 종료 시 stdout JSON 1줄:
```json
{
  "cycle_started_at": "...", "cycle_ended_at": "...", "duration_seconds": 0,
  "api_calls_total": 0, "api_calls_failed": 0,
  "entities_upserted": {"league":0,"team":0,"venue":0,"fixture":0,"fixture_detail":0,"player":0,"player_season_stat":0,"standings":0,"team_season":0},
  "translation_rows_created": {"league":0,"team":0,"player":0},
  "errors": {...}
}
```

알람: 연속 3 사이클 실패 / 401 / DB 접속 불가 / duration > 30 분. MVP 단계 stdout 만.

## 10. 인증

워커는 endpoint 아님. ADMIN 수동 트리거 (`POST /api/v1/admin/workers/daily-sync/run`) 는 별도 task — 본 spec 범위 외.

## 11. 변경 기록

| 날짜 | 변경 |
|---|---|
| 2026-05-13 | spec 작성 (be-test, W2). docs/workers/daily-sync.md SSOT mirror, L1 `league.is_active` 의존 |
