# API-Football mock fixture JSON

`tests/integration/test_daily_sync.py` 와 `tests/unit/test_daily_sync.py` 가 사용하는 고정 응답.
실 API 호출 금지 (Ultra plan quota 보호 + 결정성). 본 디렉토리에 추가/수정 시 db-schema.md
의 매핑 규칙과 db 컬럼 타입을 위반하지 않도록 주의.

## 파일

| 파일 | 의미 |
|---|---|
| `leagues_39.json` | `GET /leagues?id=39` (Premier League) |
| `leagues_2.json` | `GET /leagues?id=2` (UEFA Champions League) |
| `teams_39_2024.json` | `GET /teams?league=39&season=2024` (축약 — 2팀) |
| `teams_2_2024.json` | `GET /teams?league=2&season=2024` (축약 — 2팀) |
| `fixtures_39_2024.json` | `GET /fixtures?league=39&season=2024` (3 fixture: 종료 / 미래 / 진행 중) |
| `fixtures_2_2024.json` | `GET /fixtures?league=2&season=2024` (1 fixture: 컵 추첨 미정 NULL home/away) |
| `fixtures_events_1001.json` | events 응답 stub |
| `fixtures_statistics_1001.json` | statistics 응답 stub |
| `fixtures_lineups_1001.json` | lineups 응답 stub |
| `players_33_2024.json` | `GET /players?team=33&season=2024` (1 선수, height/weight 문자열 포함) |
| `standings_39_2024.json` | EPL standings — `group_name` 없음 |
| `standings_2_2024.json` | UCL standings — `group_name='Group A'` 포함 |

응답 구조는 API-Football v3 의 실 응답 shape 를 따른다 (`response[]` 배열 등). 컬럼 매핑은
`docs/workers/daily-sync.md` §4 참조.
