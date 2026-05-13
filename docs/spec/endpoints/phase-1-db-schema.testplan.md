# Phase 1 — DB 스키마 Test Plan

대상 spec: `docs/spec/endpoints/phase-1-db-schema.md` (정본은 `docs/spec/db-schema.md`)

## 0. 테스트 종류

| 분류 | 위치 | 의존성 | 마커 |
|---|---|---|---|
| 단위 (unit) | `tests/unit/test_db_models.py` | SQLAlchemy 모델만 (메타데이터 introspection) | `pytest -m unit` |
| 통합 (integration) | `tests/integration/test_db_schema_migration.py` | 실 Postgres (격리 schema), alembic | `pytest -m integration` |

## 1. 격리 정책

- 통합 테스트 fixture (`tests/conftest.py`) 는 `test_<run_id>_phase1` 형식의 임시 schema 를 생성 → alembic `upgrade head` 를 그 schema 에 적용 → 테스트 후 schema drop
- prod schema 직접 쿼리 / 변경 금지
- 환경변수 `TEST_DATABASE_URL` 가 없으면 통합 테스트 전체 skip

## 2. 단위 테스트 케이스 (`tests/unit/test_db_models.py`)

| ID | 케이스 | 검증 방법 | 커버 대상 |
|---|---|---|---|
| U-01 | 13 모델 import 가능 | `from app.models import (League, LeagueTranslation, Venue, Team, TeamTranslation, TeamSeason, Player, PlayerTranslation, PlayerSeasonStat, Fixture, FixtureDetail, Standings, AppUser)` | 모델 모듈 존재 |
| U-02 | `Base.metadata.tables` 가 정확히 13 테이블 포함 | 이름 set 비교 | 누락/추가 검출 |
| U-03 | 각 테이블 PK 컬럼 정의 일치 | `.primary_key.columns.keys()` | 모델 PK |
| U-04 | entity 테이블의 `external_id` UNIQUE 제약 존재 | 컬럼 `.unique` 또는 UniqueConstraint 검색 | UNIQUE |
| U-05 | `*_translation` 의 PK 가 FK 이며 ON DELETE CASCADE | FK `.ondelete == 'CASCADE'` | 1:1 강제 |
| U-06 | `team.venue_id`, `player.current_team_id`, `fixture.{home_team_id, away_team_id, venue_id}` 의 ON DELETE SET NULL | FK 검사 | SET NULL 정책 |
| U-07 | `team_season` composite PK 3 컬럼 | PK 컬럼 정렬 비교 | composite PK |
| U-08 | `player_season_stat` UNIQUE 4 컬럼 | UniqueConstraint 컬럼 set 비교 | UNIQUE |
| U-09 | `league.type` CHECK 제약 정의 | CheckConstraint sqltext 에 `'League'` 와 `'Cup'` 포함 | CHECK |
| U-10 | `app_user.role` CHECK 제약 정의 + DEFAULT 'USER' | CheckConstraint + Column.default/server_default | CHECK |
| U-11 | `fixture.home_team_id` / `away_team_id` nullable=True | 컬럼 `.nullable` | NULL 정책 |
| U-12 | `*_translation.name_ko` 등 번역 컬럼 nullable=True | 컬럼 `.nullable` | NULL 정책 |
| U-13 | `created_at/updated_at` 컬럼 server_default 존재 (해당 테이블) | server_default not None | 시각 자동화 |
| U-14 | `player_season_stat.rating` Numeric(4,2) | 타입 확인 | 타입 |
| U-15 | jsonb 컬럼 (`raw_stats`, `events`, `statistics`, `lineups`, `home_away_breakdown`, `raw_data`) JSONB 타입 | 타입 확인 | 타입 |

매핑: U-01~U-02 ⇒ 모델 모듈 구조 / U-03~U-08, U-11~U-12 ⇒ 컬럼·제약 정의 / U-09~U-10 ⇒ CHECK / U-13~U-15 ⇒ 컬럼 타입/기본값. 변경 구현 파일(`app/models/*`) 기준 ≥ 80% line 커버리지 목표.

## 3. 통합 테스트 케이스 (`tests/integration/test_db_schema_migration.py`)

테스트 시작 시 임시 schema 생성 → alembic `upgrade head` 적용 → 검증.

| ID | 케이스 | 검증 방법 |
|---|---|---|
| I-01 | 13 테이블 모두 생성됨 | `information_schema.tables` 쿼리 결과 set 비교 |
| I-02 | 모든 인덱스 생성됨 (정본 §7 일람) | `pg_indexes` 쿼리, 이름 별 존재 확인 |
| I-03 | `league.type` CHECK 동작 | `INSERT ... type='Invalid'` → IntegrityError |
| I-04 | `app_user.role` CHECK 동작 | `INSERT ... role='SUPER'` → IntegrityError; 기본값 INSERT 시 role='USER' |
| I-05 | `league.external_id` UNIQUE | 같은 external_id 두 번 INSERT → IntegrityError |
| I-06 | `team.external_id` / `team.slug` UNIQUE | 동일 |
| I-07 | `player.external_id` UNIQUE | 동일 |
| I-08 | `fixture.external_id` UNIQUE | 동일 |
| I-09 | `venue.external_id` nullable + UNIQUE (NULL 다중 허용) | NULL 인 venue 두 row INSERT 성공 |
| I-10 | `app_user.email` UNIQUE | 동일 |
| I-11 | `league_translation` PK=FK 1:1 강제 | 같은 league_id 두 번 INSERT → IntegrityError (PK 충돌) |
| I-12 | `team_translation` 1:1 강제 | 동일 |
| I-13 | `player_translation` 1:1 강제 | 동일 |
| I-14 | `team_season` composite PK | 같은 3-tuple 두 번 INSERT → IntegrityError |
| I-15 | `player_season_stat` UNIQUE(4-tuple) | 같은 4-tuple 두 번 INSERT → IntegrityError |
| I-16 | `standings` UNIQUE w/ COALESCE | (league, season, team, NULL) 와 (league, season, team, NULL) 두 번 INSERT → 두 번째 실패; (league, season, team, 'Group A') 이후 동일 4-tuple 도 실패; (league, season, team, 'Group A') vs (league, season, team, 'Group B') 는 모두 성공 |
| I-17 | ON DELETE CASCADE — league → league_translation | league INSERT, translation INSERT, league DELETE → translation row 사라짐 |
| I-18 | ON DELETE CASCADE — team → team_translation, team_season, player_season_stat, standings | team 삭제 시 종속 row 모두 사라짐 |
| I-19 | ON DELETE CASCADE — player → player_translation, player_season_stat | 동일 |
| I-20 | ON DELETE CASCADE — fixture → fixture_detail | 동일 |
| I-21 | ON DELETE CASCADE — league → fixture | 동일 |
| I-22 | ON DELETE SET NULL — venue → team.venue_id, fixture.venue_id | venue 삭제 시 두 FK NULL |
| I-23 | ON DELETE SET NULL — team → player.current_team_id, fixture.home_team_id, fixture.away_team_id | team 삭제 시 NULL (단 player 자체는 유지, fixture 자체는 유지) |
| I-24 | `fixture.home_team_id / away_team_id` NULL 허용 | 두 컬럼 NULL 로 fixture INSERT 성공 (컵 추첨 미정 시나리오) |
| I-25 | `*_translation.name_ko` NULL INSERT 후 영문 fallback 가능 | NULL 인 채 INSERT 성공 (fallback 로직은 spec 외이지만 NULL 허용은 강제) |
| I-26 | `created_at/updated_at` 자동 채움 | `INSERT INTO league(...)` 후 두 컬럼 not null |
| I-27 | `player_season_stat.rating` Numeric 정확도 | `7.13` INSERT 후 SELECT 시 `Decimal('7.13')` 반환 |
| I-28 | alembic downgrade head → base 가 13 테이블 모두 drop | downgrade 후 `information_schema.tables` 에 없음 |

매핑: I-01~I-02 ⇒ DDL 생성, I-03~I-10 ⇒ CHECK + UNIQUE, I-11~I-16 ⇒ 번역 1:1 / composite PK / partial unique, I-17~I-23 ⇒ FK action, I-24~I-25 ⇒ NULL 정책, I-26~I-27 ⇒ 컬럼 default / type, I-28 ⇒ migration reversibility.

## 4. Red 단계 기대

- 본 spec 단계에서 모델 / 마이그레이션 미작성 → 단위 테스트는 import 단계에서 ModuleNotFoundError, 통합 테스트는 schema/모델 부재로 fail. **이게 정상 (TDD Red).**
- be-dev 작업 후 모든 케이스 PASS 가 DoD.

## 5. 커버리지 목표

- 변경 구현 파일 (예상): `app/models/__init__.py`, `app/models/<entity>.py`, `alembic/versions/<rev>_phase1_initial_schema.py`.
- 위 통합 테스트가 마이그레이션 전체를 실행하므로 마이그레이션 line 커버리지 ≈ 100%. 모델 코드는 ORM 사용 (단위 + 통합) 으로 ≥ 80% 달성 예상.

## 6. 외부 의존성 mock 정책

- 본 task 는 외부 API 의존성 없음. API-Football / OpenAI 호출 발생하면 spec 위반 → reviewer 가 REQUEST_CHANGES.
- Supabase: 통합 테스트에서 실 Postgres (격리 schema) 만 사용.
