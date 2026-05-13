# W1 — translation-filler Test Plan

대상 spec: `docs/spec/endpoints/phase-5-translation-filler.md`
정본: `docs/workers/translation-filler.md`

## 0. 분류

| 분류 | 파일 | 의존성 | 마커 |
|---|---|---|---|
| 단위 | `tests/unit/test_translation_filler.py` | mock OpenAI, mock SQLAlchemy/세션. DB 없음 | `pytest -m unit` |
| 통합 | `tests/integration/test_translation_filler.py` | 격리 schema 실 Postgres + mock OpenAI client (비용/외부 의존 회피) | `pytest -m integration` |

## 1. 격리 / mock 정책

- 통합 테스트는 `tests/conftest.py` 의 `isolated_db` fixture 사용. prod schema 미접근
- **OpenAI 는 통합에서도 mock**. 실 호출 금지 (CLAUDE.md §11 비용 정책, agent-workflow.md §8)
- be-test 의 권한 경계 (be-test.md §"권한 경계"): 외부 API 통합 호출 시 API-Football 만 허용, OpenAI 호출 금지

## 2. 단위 테스트 (`tests/unit/test_translation_filler.py`)

| ID | 케이스 | 검증 |
|---|---|---|
| TF-U-01 | 큐 조회 SQL 정확성 | 빌더 / 함수가 만든 SQL 문자열 또는 SQLAlchemy 구문에 (a) `team_translation` JOIN `team`, (b) `player_translation` JOIN `player`, (c) `name_ko IS NULL OR short_name_ko IS NULL`, (d) `UNION ALL` 포함. **league 미포함** 명시 (league 는 ADMIN manual). |
| TF-U-02 | 큐 비었을 때 즉시 종료 | mock DB 가 빈 결과 반환 → entry 함수가 즉시 return, mock OpenAI client 호출 0회 |
| TF-U-03 | few-shot prompt 빌더 | (a) entity_type=player + nationality='England' → 시드 CSV 에서 England 5~10건 포함된 prompt 생성; (b) entity_type=team + country='England' → team_translation 시드에서 매칭. 매칭 0건이면 fallback 5건 포함 |
| TF-U-04 | OpenAI 응답 JSON 파싱 | (a) 정상 `{"name_ko": "...", "short_name_ko": "..."}` → 둘 다 반환; (b) 깨진 JSON → 함수가 None 또는 예외 처리 후 None 반환; (c) `name_ko` 만 있고 `short_name_ko` 누락 → skip 처리; (d) 빈 문자열 → skip |
| TF-U-05 | OpenAI 호출 파라미터 | mock 캡처: `model="gpt-3.5-turbo"`, `temperature=0`, `max_tokens=100`, `response_format={"type":"json_object"}` |
| TF-U-06 | 배치 상한 50 적용 | mock DB 큐가 200 row 반환 → 한 사이클이 OpenAI 호출을 50회 이하로 |
| TF-U-07 | semaphore=5 동시성 | mock OpenAI 호출이 동시 5개 이상이 되지 않음. asyncio 환경에서 측정 (혹은 동시 호출 카운터 패턴) |
| TF-U-08 | 지수 백오프 1s/2s/4s × 3회 | mock OpenAI 가 5xx 3회 반환 → row skip. `asyncio.sleep` mock 으로 호출 인자 캡처. 인자 = [1, 2, 4] (대략) |
| TF-U-09 | league 처리 제외 | 큐 SQL 빌더 출력에 `league_translation` 이 처리 대상으로 포함되지 않음. 또는 처리 함수가 entity_type='league' 인 입력을 skip |

매핑: TF-U-01 ⇒ 큐 SQL, TF-U-02 ⇒ early-exit, TF-U-03 ⇒ prompt 빌더, TF-U-04 ⇒ 응답 파서, TF-U-05 ⇒ API 파라미터, TF-U-06/07 ⇒ 운영 파라미터, TF-U-08 ⇒ 재시도 정책, TF-U-09 ⇒ 정책 가드.

## 3. 통합 테스트 (`tests/integration/test_translation_filler.py`)

격리 schema 에 alembic upgrade head 적용. seed row 직접 INSERT → 워커 entry 호출 → 결과 검증.
OpenAI 는 monkeypatch 로 mock.

| ID | 케이스 | 검증 |
|---|---|---|
| TF-I-01 | 큐 5 row, mock OpenAI 정상 응답 | INSERT 5 team_translation + player_translation (name_ko=NULL) → mock 이 항상 `{"name_ko":"X","short_name_ko":"X"}` 반환 → 워커 1 사이클 → 모든 5 row 가 not null |
| TF-I-02 | 큐 비었을 때 즉시 종료 | INSERT 없이 워커 호출 → mock OpenAI 호출 0회, 사이클 duration < 1초 |
| TF-I-03 | OpenAI 5xx → 재시도 후 row skip | mock 이 항상 5xx → 1 row 입력 → 워커 종료 후 해당 row 여전히 name_ko=NULL, mock 호출 3회 (1+2+4 sleep) |
| TF-I-04 | JSON 깨짐 | mock 응답 = `"this is not json"` → row skip, NULL 유지 |
| TF-I-05 | 멱등성 | row name_ko 채운 뒤 워커 재실행 → 그 row 미처리 (mock 호출 0회) |
| TF-I-06 | 보호: 채워진 row 덮어쓰기 금지 | 미리 name_ko='기존' 으로 INSERT → 워커 호출 → 여전히 '기존' (UPDATE 발생 안 함) |
| TF-I-07 | 1분 폴링 스케줄러 진입점 | 스케줄러 모듈 import 가능 + 1분 주기 등록 호출 검증 (mock APScheduler 또는 호출 인자 캡처) |

매핑: TF-I-01 정상 / TF-I-02 빈 큐 / TF-I-03 OpenAI 5xx / TF-I-04 JSON 깨짐 / TF-I-05~06 멱등 + 덮어쓰기 금지 / TF-I-07 스케줄러.

## 4. Red 단계 기대

- 본 spec 단계에서 `app/workers/translation_filler/` 미생성. 단위 / 통합 모두 ImportError 로 fail. **TDD Red 정상.**
- be-dev 작업 후 모든 케이스 PASS 가 DoD.

## 5. 커버리지 목표

- 변경 구현 파일 예상: `app/workers/translation_filler/__init__.py`, `app/workers/translation_filler/queue.py`, `app/workers/translation_filler/prompt.py`, `app/workers/translation_filler/runner.py`, `app/workers/translation_filler/scheduler.py` (be-dev 자유)
- 위 테스트가 entry 함수 + queue SQL + prompt 빌더 + 응답 파서 + 재시도 + scheduler 등록까지 실행하므로 ≥ 80% line coverage 가능

## 6. 외부 의존성 mock 정책

| 의존성 | unit | integration |
|---|---|---|
| OpenAI | mock (AsyncMock 권장) | mock (monkeypatch on openai 클라이언트). **실 호출 금지** |
| Supabase | mock in-memory | 실 Postgres 격리 schema |
| APScheduler | mock | mock (scheduler 등록 호출만 검증, 실 1분 sleep 금지) |
| 시드 CSV `_Player__202605131748.csv` | fixture: 작은 stub CSV in tests/fixtures/, 또는 실파일 일부 row | 동일 |
