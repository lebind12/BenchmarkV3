# L3 — `h2h_fixture` Test Plan

대상 spec: `docs/spec/endpoints/phase-1-followup-l3.md`

## 0. 분류

| 분류 | 파일 | 의존성 |
|---|---|---|
| 단위 | `tests/unit/test_l3_h2h_models.py` | SQLAlchemy 메타데이터 |
| 통합 | `tests/integration/test_l3_h2h_migration.py` | 격리 schema + alembic + L2 머지 |

## 1. 사전 조건

- L2 (`0003_transfer_injury_news`) 가 main 에 머지된 상태에서만 통합 테스트가 정상 동작. 그 전에는 alembic upgrade head 가 0003 dependency missing 으로 fail (정상 Red).
- 단위는 모델 정의만 보므로 L2 의존성 무관 (단, `Base.metadata` 에 L2 의 3 테이블이 있어야 17 테이블 회귀가 의미 있음).

## 2. 단위 (`tests/unit/test_l3_h2h_models.py`)

| ID | 케이스 | 검증 |
|---|---|---|
| L3U-01 | `H2HFixture` import 가능 | `from app.models import H2HFixture` |
| L3U-02 | metadata 가 17 테이블 포함 | (기존 16 + h2h_fixture) |
| L3U-03 | 컬럼 / 타입 / NULL | id(PK), external_id integer NOT NULL UNIQUE, home_team_id NOT NULL FK CASCADE, away_team_id NOT NULL FK CASCADE, league_external_id integer nullable, league_name text nullable, season_year integer nullable, kickoff_at timestamptz NOT NULL, status_short text nullable, goals_home/goals_away smallint nullable, raw_data JSONB nullable, created_at/updated_at NOT NULL server_default |
| L3U-04 | `external_id` UNIQUE | 단일 컬럼 unique or UniqueConstraint |
| L3U-05 | `h2h_pair_idx` 모델 선언 + LEAST/GREATEST 함수 | 인덱스 이름 존재, 표현식에 `least(`, `greatest(`, `desc` 포함 (대소문자 무관) |

## 3. 통합 (`tests/integration/test_l3_h2h_migration.py`)

격리 schema 에 alembic upgrade head (0001+0002+0003+0004) 적용 후 검증.

| ID | 케이스 | 검증 |
|---|---|---|
| L3I-01 | upgrade head 후 17 테이블 | information_schema 결과 set |
| L3I-02 | `h2h_pair_idx` 함수 인덱스 생성 + LEAST/GREATEST 포함 | `pg_indexes.indexdef` 에 `LEAST`, `GREATEST`, `kickoff_at DESC` 포함 (대소문자 무관) |
| L3I-03 | `external_id` UNIQUE | 같은 external_id 두 번째 INSERT → IntegrityError |
| L3I-04 | `home_team_id`, `away_team_id` NOT NULL | 한쪽 NULL INSERT → IntegrityError |
| L3I-05 | `league_external_id` NULL 허용 (외부 대회) | NULL 로 INSERT 성공, league_name='Friendlies' 보관 |
| L3I-06 | FK CASCADE — team 삭제 시 row 사라짐 | team 삭제 → h2h_fixture row 사라짐 |
| L3I-07 | 함수 인덱스 쿼리 — 순서 무관 H2H 조회 | (home=A, away=B) 와 (home=B, away=A) row 모두 같은 LEAST/GREATEST 쌍에 대해 1번 쿼리로 반환 |
| L3I-08 | downgrade -1 후 h2h_fixture drop, 다른 16 테이블 유지 | information_schema 검사 |
| L3I-09 | downgrade base → upgrade head reversibility | 17 테이블 재생성 |

## 4. Red 단계 기대

- `app/models/H2HFixture` 미정의 → 단위 ImportError fail
- L2 가 머지 안 된 상태에서는 alembic 의 0003 revision 자체가 없어 `upgrade head` 가 fail (revision-not-found 또는 0001/0002 까지만 올라감)
- L2 머지 + L3 의 0004 마이그레이션 생성 후 모두 PASS = DoD

## 5. 커버리지

- 변경 구현 파일: `app/models/h2h_fixture.py`, `alembic/versions/0004_h2h_fixture.py`
- 통합이 upgrade + downgrade + 함수 인덱스 쿼리 모두 실행 → ≈ 100% line coverage 가능

## 6. 외부 의존성 mock

없음. 격리 schema 만.
