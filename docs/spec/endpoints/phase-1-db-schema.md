# Phase 1 — DB 스키마 (SSOT 미러)

본 문서는 BE 워크플로(test → dev → reviewer) 의 **spec 산출물** 이며, endpoint 가 아닌 **DB 인프라 task** 의 요구사항 정본 mirror 다.
정본은 `docs/spec/db-schema.md`. **본 task 는 그 13 테이블을 정확히 그대로 구현하는 것** 이다.

> ⚠️ **불변 원칙** (dev 가 임의로 위반하면 reviewer 는 REQUEST_CHANGES)
> - 13 테이블 외 추가 테이블 작성 금지
> - 13 테이블 중 하나도 누락 금지
> - 컬럼 추가 / 삭제 / 타입 변경 금지 (이름, 타입, NULL, DEFAULT, CHECK, FK action 모두 정본과 일치)
> - 인덱스 / UNIQUE / PRIMARY KEY 도 정본 §3, §4, §7 일람과 일치
> - 수정 필요 시 본 task 가 아니라 **`docs/spec/db-schema.md` 를 먼저 PR** 로 변경

## 1. 범위

- 산출물: SQLAlchemy 모델 13개 + 단일 alembic 마이그레이션 (`upgrade` 로 13 테이블 + 인덱스 + 제약 모두 생성, `downgrade` 로 모두 drop).
- be-dev 가 작업할 디렉토리: `app/models/`, `alembic/versions/`. 본 spec 단계의 be-test 는 `app/` 을 수정하지 않는다.

## 2. 13 테이블 체크리스트

| # | 테이블 | 핵심 제약 |
|---|---|---|
| 1 | `league` | PK `id`, UNIQUE `external_id`, UNIQUE `slug`, CHECK `type IN ('League','Cup')`, idx `(type)` |
| 2 | `league_translation` | PK `league_id` (FK→`league.id` ON DELETE CASCADE) |
| 3 | `venue` | PK `id`, UNIQUE `external_id` (nullable) |
| 4 | `team` | PK `id`, UNIQUE `external_id`, UNIQUE `slug`, FK `venue_id` → `venue.id` ON DELETE SET NULL, idx `(country)`, idx `(venue_id)` |
| 5 | `team_translation` | PK `team_id` (FK→`team.id` ON DELETE CASCADE) |
| 6 | `team_season` | composite PK `(team_id, league_id, season_year)`, 두 FK 모두 ON DELETE CASCADE, idx `(league_id, season_year)` |
| 7 | `player` | PK `id`, UNIQUE `external_id`, UNIQUE `slug`, FK `current_team_id` → `team.id` ON DELETE SET NULL, idx `(current_team_id)`, idx `(nationality)` |
| 8 | `player_translation` | PK `player_id` (FK→`player.id` ON DELETE CASCADE) |
| 9 | `player_season_stat` | PK `id`, UNIQUE `(player_id, team_id, league_id, season_year)`, 세 FK 모두 ON DELETE CASCADE, idx `(player_id)`, idx `(team_id, season_year)`, idx `(league_id, season_year, goals DESC)` |
| 10 | `fixture` | PK `id`, UNIQUE `external_id`, FK `league_id` ON DELETE CASCADE, FK `home_team_id/away_team_id/venue_id` ON DELETE SET NULL, `home_team_id/away_team_id` **NULL 허용** (컵 추첨 미정), idx `(league_id, season_year)`, idx `(kickoff_at)`, idx `(status_short)`, idx `(home_team_id)`, idx `(away_team_id)` |
| 11 | `fixture_detail` | PK `fixture_id` (FK→`fixture.id` ON DELETE CASCADE) |
| 12 | `standings` | PK `id`, UNIQUE index `(league_id, season_year, team_id, COALESCE(group_name, ''))` (functional/partial — NULL 도 충돌), 두 FK 모두 ON DELETE CASCADE, idx `(league_id, season_year, rank)` |
| 13 | `app_user` | PK `id`, UNIQUE `email`, CHECK `role IN ('USER','STREAMER','ADMIN')`, DEFAULT `role='USER'`, idx `(role)` |

## 3. 컬럼 정본

각 테이블의 컬럼 / 타입 / NULL / DEFAULT 는 `docs/spec/db-schema.md` §3.1–§3.13 의 DDL 을 그대로 따른다. 본 문서는 변경점 없음.

특히:
- bigint identity PK (postgres `GENERATED ALWAYS AS IDENTITY`) — SQLAlchemy 측은 `BigInteger` + `Identity(always=True)` 사용
- `created_at`, `updated_at` 컬럼은 `timestamptz NOT NULL DEFAULT now()` — server_default `func.now()`
- `numeric(4,2)` — `Numeric(4, 2)`
- jsonb — `JSONB` (sqlalchemy.dialects.postgresql)
- text - `Text`

## 4. ON DELETE 시나리오 (정본 §4)

| 케이스 | 기대 |
|---|---|
| league row 삭제 | `league_translation` row CASCADE 삭제, `team_season` CASCADE, `fixture` CASCADE, `standings` CASCADE, `player_season_stat` CASCADE |
| venue row 삭제 | `team.venue_id` → NULL, `fixture.venue_id` → NULL |
| team row 삭제 | `team_translation` CASCADE, `team_season` CASCADE, `player.current_team_id` → NULL, `fixture.home_team_id/away_team_id` → NULL, `standings` CASCADE, `player_season_stat` CASCADE |
| player row 삭제 | `player_translation` CASCADE, `player_season_stat` CASCADE |
| fixture row 삭제 | `fixture_detail` CASCADE |

## 5. NULL 허용 (정본 §5)

- `*_translation.name_ko`, `*_translation.short_name_ko` — 번역 대기. INSERT 시 NULL 허용 필수
- `fixture.home_team_id`, `fixture.away_team_id` — 컵 추첨 미정 라운드 row 가 두 컬럼 모두 NULL 인 상태로 INSERT 가능해야 함
- `fixture.goals_*`, `fixture.score_*`, `fixture.home_winner`, `fixture.away_winner` — NULL 허용
- `team.venue_id`, `player.current_team_id`, `venue.external_id` — NULL 허용

## 6. CHECK 제약

- `league.type CHECK (type IN ('League', 'Cup'))` — 다른 값으로 INSERT 시 `IntegrityError`
- `app_user.role CHECK (role IN ('USER', 'STREAMER', 'ADMIN'))` — 다른 값 INSERT 시 `IntegrityError`. 기본값 `'USER'`

## 7. UNIQUE 시나리오

- 모든 entity 테이블의 `external_id` 두 번 INSERT → 두 번째 실패
- `venue.external_id` 는 nullable. 같은 NULL 두 row 는 충돌하지 않음 (postgres 기본 동작)
- `app_user.email` 중복 INSERT → 실패
- `team_season` 같은 `(team_id, league_id, season_year)` 두 번 INSERT → 두 번째 PK 충돌 실패
- `player_season_stat` 같은 4-tuple 두 번 INSERT → 두 번째 UNIQUE 위반
- `standings` 같은 `(league_id, season_year, team_id, group_name)` 충돌 시 실패. **`group_name = NULL` 인 row 두 개도 충돌해야 함** (COALESCE)
- `*_translation` 한 entity 에 두 번 INSERT → PK 위반 (1:1 강제)

## 8. 인덱스 일람 (정본 §3 + §7)

| 테이블 | 인덱스 |
|---|---|
| league | `league_type_idx (type)` |
| team | `team_country_idx (country)`, `team_venue_idx (venue_id)` |
| team_season | `team_season_league_year_idx (league_id, season_year)` |
| player | `player_team_idx (current_team_id)`, `player_nationality_idx (nationality)` |
| player_season_stat | `player_season_stat_player_idx`, `player_season_stat_team_year_idx`, `player_season_stat_topscorer_idx (league_id, season_year, goals DESC)` |
| fixture | `fixture_league_season_idx`, `fixture_kickoff_idx`, `fixture_status_idx`, `fixture_home_team_idx`, `fixture_away_team_idx` |
| standings | `standings_uniq` (unique, COALESCE), `standings_league_season_rank_idx` |
| app_user | `app_user_role_idx (role)` |

dev 가 인덱스 누락 시 통합 테스트가 잡는다.

## 9. DB 의존성

- DB: Supabase Postgres 14+ (또는 호환 Postgres)
- 통합 테스트는 환경변수 `TEST_DATABASE_URL` 의 DB 에 임시 schema 를 생성해서 마이그레이션을 적용. prod schema 접근 금지.
- 단위 테스트는 SQLAlchemy 모델만 import → in-memory 검증 (실 DB 무관).

## 10. 에러 케이스 / 비즈니스 규칙

- 본 task 는 schema 작성이므로 별도 비즈니스 로직 없음. 단, "13 테이블 정확 일치" 자체가 비즈니스 규칙.
- `created_at`, `updated_at` 는 서버 default (`now()`). 애플리케이션이 set 하지 않아도 자동 채워져야 함.

## 11. 인증 요구사항

- 본 task 는 endpoint 가 아님. 인증 N/A.
- 단, `app_user` 테이블 자체는 향후 인증 endpoint 의 의존성이므로 본 task 에서 생성된다.

## 12. 변경 기록

| 날짜 | 변경 |
|---|---|
| 2026-05-13 | spec 작성 (be-test). 13 테이블 정본 mirror |
