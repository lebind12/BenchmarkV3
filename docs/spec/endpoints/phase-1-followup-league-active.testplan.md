# L1 — `league.is_active` Test Plan

대상 spec: `docs/spec/endpoints/phase-1-followup-league-active.md`

## 0. 테스트 분류

| 분류 | 파일 | 의존성 | 마커 |
|---|---|---|---|
| 단위 | `tests/unit/test_league_is_active.py` | SQLAlchemy 모델 metadata 만 | `pytest -m unit` |
| 통합 | `tests/integration/test_league_is_active_migration.py` | 실 Postgres + alembic | `pytest -m integration` |

## 1. 격리 정책

- 통합은 conftest 의 `isolated_db` fixture 사용 (`test_<run_id>_<endpoint>` schema). prod 미접근.
- `TEST_DATABASE_URL` 미설정 시 conftest 가 skip.

## 2. 단위 테스트 (`tests/unit/test_league_is_active.py`)

| ID | 케이스 | 검증 |
|---|---|---|
| LU-01 | `League.is_active` 컬럼 존재 | `League.__table__.columns` 에 `is_active` 포함 |
| LU-02 | 타입은 Boolean | `isinstance(col.type, Boolean)` |
| LU-03 | NOT NULL | `col.nullable is False` |
| LU-04 | server_default 가 truthy (`'true'` / `true`) | `col.server_default` not None; 텍스트에 `true` 포함 |
| LU-05 | metadata 의 `league` 테이블 인덱스 목록에 `league_active_idx` 존재 | `tbl.indexes` 순회. 모델 측에서 인덱스 선언 안 했으면 fail 하므로 dev 가 모델에 `Index(...)` 추가하도록 강제 |
| LU-06 | 13 테이블 총 개수 변동 없음 (테이블 추가/삭제 없음) | `Base.metadata.tables` set 비교 |

매핑: LU-01~LU-04 ⇒ 모델 컬럼 정의 / LU-05 ⇒ partial index 모델 선언 / LU-06 ⇒ 회귀 방지.

## 3. 통합 테스트 (`tests/integration/test_league_is_active_migration.py`)

격리 schema 에 `alembic upgrade head` 적용 (즉 0001 + 0002 둘 다) 한 뒤 검증.

| ID | 케이스 | 검증 |
|---|---|---|
| LI-01 | upgrade head 후 `league.is_active` 컬럼 존재 + boolean + NOT NULL | `information_schema.columns` 쿼리 |
| LI-02 | `league.is_active` server default = `true` | `information_schema.columns.column_default` 가 `'true'` 포함 |
| LI-03 | `league_active_idx` 부분 인덱스 생성됨 | `pg_indexes.indexdef` 에 `WHERE is_active` 포함 |
| LI-04 | 기존 INSERT 가 default true 채움 | `INSERT INTO league (external_id, name, type, slug) VALUES (...)` 후 `is_active = true` |
| LI-05 | NULL 명시 INSERT 거절 | `INSERT ... is_active = NULL` → IntegrityError (NotNull violation) |
| LI-06 | false 토글 정상 | `UPDATE league SET is_active=false WHERE id=...` 후 select 시 false |
| LI-07 | partial index 효과 (functional 확인) | `EXPLAIN SELECT * FROM league WHERE is_active` 가 index 후보로 `league_active_idx` 를 보여줄 수 있음. 안 보여줘도 fail 처리하지 않음 (planner 의존). 인덱스 존재 자체 확인만 강제 |
| LI-08 | `alembic downgrade -1` 후 컬럼 + 인덱스 모두 제거 | downgrade 후 information_schema 에서 컬럼/인덱스 사라짐. **그리고 league 테이블 자체는 여전히 존재 (13 테이블 유지)**. 이후 upgrade head 로 다시 복구되어도 idempotent |
| LI-09 | `0001_initial_schema` 단독 적용 (0002 미적용) 상태에서는 컬럼 없음 | `alembic downgrade 0001_initial_schema` (= -1) 후 컬럼 부재 확인 (LI-08 와 동일 단계, 분리 케이스로 명시) |

매핑: LI-01~LI-03 ⇒ 마이그레이션 결과 / LI-04~LI-06 ⇒ default + NOT NULL + 토글 / LI-07 ⇒ 인덱스 존재 / LI-08~LI-09 ⇒ reversibility.

## 4. Red 단계 기대

- 본 spec 단계에서 `app/models/league.py` 의 `League` 클래스에 `is_active` 미정의 → 단위 LU-01~LU-05 fail (assert false 또는 attribute 부재).
- `alembic/versions/0002_*.py` 미생성 → 통합 LI-01~LI-09 fail (upgrade head 가 0001 까지만 적용, 컬럼/인덱스 없음).
- be-dev 작업 후 모든 케이스 PASS 가 DoD.

## 5. 커버리지 목표

- 변경 구현 파일 (예상): `app/models/league.py` (한 줄 추가), `alembic/versions/0002_league_is_active.py` (upgrade/downgrade).
- 위 통합 테스트가 upgrade + downgrade 모두 실행하므로 마이그레이션 ≈ 100% line coverage.

## 6. 외부 의존성 mock

- 본 task 외부 API 의존성 없음. Supabase 만 사용 (격리 schema).
