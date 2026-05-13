# W2 — daily-sync Test Plan

대상 spec: `docs/spec/endpoints/phase-4-daily-sync.md` / 정본 `docs/workers/daily-sync.md`

## 0. 분류

| 분류 | 파일 | 의존성 | 마커 |
|---|---|---|---|
| 단위 | `tests/unit/test_daily_sync.py` | mock API-Football (고정 fixture JSON), mock SQLAlchemy. DB 없음 | `pytest -m unit` |
| 통합 | `tests/integration/test_daily_sync.py` | 격리 schema 실 Postgres + mock API-Football client | `pytest -m integration` |

## 1. 격리 / mock 정책

- 통합 테스트는 conftest 의 `isolated_db` fixture 사용. prod schema 미접근
- **API-Football 통합에서도 mock 고정 fixture JSON 사용** — 본 spec 단계에서 결정적 테스트 + API quota 보호
  - 통합 시 실 API 호출은 별도 smoke task 에서. 본 testplan 범위 외
- 고정 fixture JSON: `tests/fixtures/api_football/` (be-test 가 작성)
- be-test 권한 경계 (be-test.md §"권한 경계"): 통합 시 API-Football 호출 허용. 본 task 에서는 비용/결정성 이유로 mock 채택

## 2. 단위 테스트 (`tests/unit/test_daily_sync.py`)

| ID | 케이스 | 검증 |
|---|---|---|
| DS-U-01 | Step 1: 리그 메타 sync | mock `GET /leagues?id=` 응답 → 함수가 `league` upsert 호출, 컬럼 매핑 (id→external_id, country.{name,code,flag}→country_*, seasons[current=true].year→current_season) |
| DS-U-02 | Step 2: 팀 + venue upsert | mock `GET /teams?league=&season=` 응답 → venue 먼저 upsert → team upsert with venue_id, slug=`<slugify(name)>-<external_id>` |
| DS-U-03 | Step 3: fixture 목록 + 컵 추첨 NULL | mock 응답 중 `teams.home.id=null` row → fixture INSERT with `home_team_id=NULL`. 정상 row 는 home/away 채워짐 |
| DS-U-04 | Step 4: 활성 fixture 큐 SQL | 빌더 함수가 만든 SQL 텍스트에 `48 hours`, `14 days`, `status_short NOT IN ('FT', 'AET', 'PEN', 'CANC', 'PST')`, `league_id IN (...)` 포함 |
| DS-U-05 | Step 5: fixture_detail 3 calls 묶음 | mock events/statistics/lineups 3 응답 → `fixture_detail` upsert 시 3 JSONB 컬럼 모두 채워짐, `fetched_at` not null |
| DS-U-06 | Step 6: 선수 + height/weight 파싱 | mock `GET /players?team=&season=` 응답 → height `'188 cm'`→188, weight `'78 kg'`→78. 파싱 실패 케이스 (`'unknown'`) → NULL. API typo `appearences` → `appearances` 컬럼 매핑 |
| DS-U-07 | Step 7: standings group_name 처리 | mock UCL group stage 응답 → group_name='Group A'/'Group B'; EPL 응답 → group_name=NULL |
| DS-U-08 | Step 8: team_season 정션 upsert | step 3 결과의 (league, season, team) 집합으로 INSERT ON CONFLICT DO NOTHING. mock conn 의 SQL 호출 검사 |
| DS-U-09 | Step 9: 번역 row 보장 | new league/team/player id 마다 INSERT ON CONFLICT (entity_id) DO NOTHING. SQL 검사 |
| DS-U-10 | semaphore=6 동시성 | mock API 가 1초 sleep → 동시 in-flight ≤ 6 |
| DS-U-11 | 백오프 1s/2s/4s × 3회 | mock API 가 항상 5xx → 호출 4회 (1+3 retry), sleep 인자 [1,2,4] |
| DS-U-12 | 멱등성 (응답 → 응답) | 같은 mock 응답 2회 적용 → upsert SQL 같은 횟수, 결과 set 동일 (in-memory store mock 으로 확인) |
| DS-U-13 | 활성 league 동적 조회 | `WHERE is_active = true` 인 league 만 처리. mock DB 가 5리그 + 1 inactive 반환 → API 호출은 활성만 |
| DS-U-14 | 에러 분기 | (a) 401 → fatal abort (cycle 예외 raise 또는 abort flag); (b) 5xx → 백오프 후 row skip; (c) 4xx → 즉시 row skip (재시도 X); (d) 응답 JSON 깨짐 → entity skip |

매핑: DS-U-01~09 ⇒ step 별 파싱/매핑/SQL, DS-U-10/11 ⇒ 운영 파라미터, DS-U-12 ⇒ 멱등성, DS-U-13 ⇒ is_active 동적 게이트, DS-U-14 ⇒ 에러 분기.

## 3. 통합 테스트 (`tests/integration/test_daily_sync.py`)

격리 schema 에 alembic upgrade head 적용 → league seed 5리그 (is_active=true) INSERT → mock API client 주입 → 사이클 호출 → DB 상태 검증.

| ID | 케이스 | 검증 |
|---|---|---|
| DS-I-01 | 빈 DB + 5리그 seed → 1 사이클 | 사이클 후 league (5), venue (>0), team (>0), fixture (>0), fixture_detail (>0), player (>0), player_season_stat (>0), standings (>0), team_season (>0), `*_translation` (>0, 한글 NULL) 모두 존재 |
| DS-I-02 | 멱등성 | 같은 mock 응답으로 2회 실행 → 각 테이블 row count 동일 (UNION 변화 없음) |
| DS-I-03 | 활성 fixture 큐 동작 | seed: 종료된 fixture (status=FT, kickoff_at = 60h 전) + 종료 직후 (kickoff_at = 24h 전) + 미래 fixture (3d 후) → Step 5 mock 이 detail 호출한 fixture set 이 (종료 직후) + (미래) 만 포함, (60h 전 종료) 미포함 |
| DS-I-04 | 컵 추첨 미정 라운드 | mock fixture 응답에 `teams.home.id=null` 인 row 포함 → 사이클 후 그 fixture row 의 home_team_id / away_team_id NULL |
| DS-I-05 | is_active=false league skip | seed 중 1 league 를 is_active=false 로 만들고 mock 응답은 그 league 도 포함 → 사이클 후 그 league 관련 fixture/team 등은 mock 응답에 있어도 API 호출 자체가 일어나지 않음 (mock 호출 카운터로 검증) |
| DS-I-06 | 번역 한글 보호 | seed 로 `team_translation (team_id=X, name_ko='맨유')` 미리 INSERT → 사이클 후 동일 row 의 name_ko 여전히 '맨유' (덮어쓰기 안 됨) |
| DS-I-07 | Step 5 일부 fixture detail mock 실패 | mock 이 특정 fixture_id 에만 5xx 3회 반환 → 그 fixture 의 fixture_detail row 미생성, 사이클 자체는 종료. 다음 사이클 (mock 정상화) 에서 그 fixture_detail row 생성됨 |

매핑: DS-I-01 정상 / DS-I-02 멱등 / DS-I-03 큐 임계치 / DS-I-04 NULL 정책 / DS-I-05 is_active 게이트 / DS-I-06 번역 보호 / DS-I-07 부분 실패 회복.

## 4. Red 단계 기대

- 본 spec 단계에서 `app/workers/daily_sync/` 미생성 → unit/integration 모두 ImportError 로 fail. **TDD Red 정상.**
- be-dev 작업 후 모든 케이스 PASS 가 DoD.

## 5. 커버리지 목표

- 변경 구현 파일 예상: `app/workers/daily_sync/{__init__,runner,steps,api_client,parsers,scheduler}.py` (모듈 분할 dev 자유)
- 통합 테스트가 9 step 전 step 실행 → ≥ 80% line coverage 가능

## 6. mock fixture JSON 위치 / 인터페이스

```
tests/fixtures/api_football/
├── leagues_39.json                # /leagues?id=39 (Premier League)
├── leagues_2.json                 # /leagues?id=2  (UCL)
├── teams_39_2024.json             # /teams?league=39&season=2024 (PL teams)
├── teams_2_2024.json              # /teams?league=2&season=2024
├── fixtures_39_2024.json          # /fixtures?league=39&season=2024
├── fixtures_2_2024.json           # /fixtures?league=2&season=2024 (with home/away NULL row)
├── fixtures_events_<fid>.json
├── fixtures_statistics_<fid>.json
├── fixtures_lineups_<fid>.json
├── players_<tid>_2024.json
└── standings_39_2024.json         # 리그 standings (group_name=NULL)
└── standings_2_2024.json          # UCL standings (group_name='Group A'..)
```

dev 의 API client 구현은 이 fixture JSON 을 mock 으로 사용 가능하도록 `httpx.AsyncClient` 또는 직접 호출자를 주입 받는 형태여야 함 (dependency injection).

가정 인터페이스 (dev 합의):
```
class APIFootballClient(Protocol):
    async def get_leagues(self, *, external_id: int) -> dict
    async def get_teams(self, *, league: int, season: int) -> dict
    async def get_fixtures(self, *, league: int, season: int) -> dict
    async def get_fixture_events(self, *, fixture: int) -> dict
    async def get_fixture_statistics(self, *, fixture: int) -> dict
    async def get_fixture_lineups(self, *, fixture: int) -> dict
    async def get_players(self, *, team: int, season: int, page: int = 1) -> dict
    async def get_standings(self, *, league: int, season: int) -> dict
```

`run_cycle(session, api_client, *, semaphore=6) -> CycleResult` 가 entry.
