# L2 — transfer / injury / news_article Test Plan

대상 spec: `docs/spec/endpoints/phase-1-followup-l2.md`

## 0. 분류

| 분류 | 파일 | 의존성 | 마커 |
|---|---|---|---|
| 단위 | `tests/unit/test_l2_models.py` | SQLAlchemy 메타데이터 | `pytest -m unit` |
| 통합 | `tests/integration/test_l2_migration.py` | 격리 schema 실 Postgres + alembic | `pytest -m integration` |

## 1. 단위 (`tests/unit/test_l2_models.py`)

| ID | 케이스 | 검증 |
|---|---|---|
| L2U-01 | `Transfer`, `Injury`, `NewsArticle` import 가능 | `from app.models import Transfer, Injury, NewsArticle` |
| L2U-02 | metadata 가 16 테이블 포함 | (기존 13 + 신규 3) |
| L2U-03 | `transfer` 컬럼/타입/NULL | id(PK), player_id NOT NULL FK CASCADE, transfer_date date NOT NULL, type text nullable, from_team_id FK SET NULL, to_team_id FK SET NULL, raw_data JSONB nullable, created_at/updated_at NOT NULL with server_default |
| L2U-04 | `transfer_uniq` UNIQUE 4 컬럼 | UniqueConstraint columns set = {player_id, transfer_date, from_team_id, to_team_id} |
| L2U-05 | transfer 인덱스 4개 | `transfer_player_idx`, `transfer_date_idx`, `transfer_to_team_idx`, `transfer_from_team_idx` |
| L2U-06 | `injury` 컬럼/타입/NULL | id, player_id NOT NULL CASCADE, fixture_id nullable SET NULL, team_id NOT NULL CASCADE, league_id NOT NULL CASCADE, season_year integer NOT NULL, type/reason text nullable, raw_data JSONB nullable, reported_at timestamptz nullable |
| L2U-07 | `injury_uniq` UNIQUE 4 컬럼 | columns set = {player_id, fixture_id, league_id, season_year} |
| L2U-08 | injury 인덱스 (partial 포함) | `injury_player_idx`, `injury_team_season_idx`, `injury_fixture_idx` (partial WHERE fixture_id IS NOT NULL) |
| L2U-09 | `news_article` 컬럼/타입/NULL | id, source NOT NULL text, source_url NOT NULL UNIQUE, original_title NOT NULL, original_summary nullable, published_at NOT NULL, image_url nullable, title_ko/summary_ko nullable, translated_at nullable, tags JSONB nullable |
| L2U-10 | news_article 인덱스 (partial + GIN) | `news_article_published_idx`, `news_article_pending_idx` (partial WHERE title_ko IS NULL), `news_article_tags_gin` (USING gin) |
| L2U-11 | 회귀: 기존 13 테이블 변경 없음 | `league.is_active` 컬럼 여전히 존재, 다른 테이블 그대로 |

## 2. 통합 (`tests/integration/test_l2_migration.py`)

격리 schema 에 `alembic upgrade head` (0001 + 0002 + 0003) 적용 후 검증.

| ID | 케이스 | 검증 |
|---|---|---|
| L2I-01 | upgrade head 후 16 테이블 존재 | `information_schema.tables` 결과 set 비교 |
| L2I-02 | 인덱스 11개 (3 신규 테이블) 생성 | `pg_indexes` 쿼리 |
| L2I-03 | `transfer` INSERT 정상 (FK 정상) | player + team 2개 INSERT → transfer INSERT |
| L2I-04 | `transfer` FK NULL 허용 (Free transfer) | from_team_id=NULL 로 INSERT 성공 |
| L2I-05 | `transfer_uniq` 위반 (정확 동일 4-tuple) | 같은 4-tuple 두 번 INSERT → 두 번째 IntegrityError |
| L2I-06 | `transfer` ON DELETE — player CASCADE | player 삭제 시 transfer row 사라짐 |
| L2I-07 | `transfer` ON DELETE — team SET NULL | from_team 삭제 시 transfer.from_team_id NULL, transfer 자체 유지 |
| L2I-08 | `injury` INSERT 정상 + UNIQUE 동작 | (player, fixture, league, season) 두 번째 INSERT → IntegrityError |
| L2I-09 | `injury.fixture_id` NULL 허용 | fixture_id NULL 로 INSERT 성공 |
| L2I-10 | `injury` partial index `WHERE fixture_id IS NOT NULL` 존재 | `pg_indexes.indexdef` 에 `WHERE fixture_id IS NOT NULL` 포함 |
| L2I-11 | `injury` ON DELETE 정책 — fixture SET NULL / team CASCADE | fixture 삭제 시 injury.fixture_id NULL; team 삭제 시 injury row 사라짐 |
| L2I-12 | `news_article.source_url` UNIQUE | 같은 URL 두 번째 INSERT → IntegrityError |
| L2I-13 | `news_article.tags` JSONB INSERT + GIN 인덱스 조회 | `INSERT ... tags='{"teams":[33]}'::jsonb` → `SELECT ... WHERE tags @> '{"teams":[33]}'::jsonb` 결과 1 row |
| L2I-14 | `news_article` partial index `WHERE title_ko IS NULL` 존재 | indexdef 검사 |
| L2I-15 | downgrade -1 후 3 테이블 모두 drop, 기존 13 테이블 유지 | information_schema 검사 + `league.is_active` 여전히 존재 |
| L2I-16 | downgrade base 정상 reversibility | 0001+0002+0003 → 0 → upgrade head 다시 가능 (idempotent revision chain) |

## 3. Red 단계 기대

- 본 spec 단계에서 `app/models/Transfer/Injury/NewsArticle` 미정의 → 단위 fail.
- `alembic/versions/0003_*.py` 미생성 → 통합 fail (16 테이블 set mismatch 등).
- dev 작업 후 모든 케이스 PASS = DoD.

## 4. 커버리지 목표

- 변경 구현 파일: `app/models/{transfer,injury,news_article}.py` (한 줄 ~ 수십 줄), `alembic/versions/0003_*.py`
- 통합 테스트가 upgrade + downgrade 모두 실행 → 마이그레이션 ≈ 100% line coverage

## 5. 외부 의존성 mock 정책

- 외부 API 의존성 없음. Supabase 격리 schema 만 사용.
