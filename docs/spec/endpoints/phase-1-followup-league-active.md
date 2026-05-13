# Phase 1 Follow-up L1 — `league.is_active` 컬럼 추가

본 문서는 BE 워크플로 spec 산출물이며, endpoint 가 아닌 **DB 인프라 변경 (additive migration)** 의 요구사항 mirror 다.
정본은 `docs/spec/db-schema.md` §3.1 (2026-05-13 갱신 — `is_active` 컬럼 + `league_active_idx` 추가됨).

> ⚠️ **불변 원칙**
> - 본 task 는 `league` 테이블에 `is_active` 컬럼과 `league_active_idx` 부분 인덱스를 추가하는 **단일 마이그레이션** 만 생성한다
> - 기존 마이그레이션 `0001_initial_schema.py` 는 **절대 수정 금지** (이미 적용되었을 수 있는 대상 환경 보호)
> - 다른 컬럼 / 테이블 / 인덱스 변경 금지

## 1. 범위

| 항목 | 변경 |
|---|---|
| 모델 | `app/models/league.py` 의 `League` 클래스에 `is_active: Mapped[bool]` 추가 |
| 마이그레이션 | 신규 `alembic/versions/<...>_0002_league_is_active.py` |
| 컬럼 | `league.is_active boolean NOT NULL DEFAULT true` |
| 인덱스 | `league_active_idx ON league (is_active) WHERE is_active` (partial index) |
| 의미 | daily-sync 가 `WHERE is_active = true` 인 리그만 처리. ADMIN endpoint 로 토글 가능. 초기 5리그 시드 시 모두 true |

본 task 의 be-dev 영역: `app/models/league.py`, `alembic/versions/0002_*.py`. 본 spec 단계의 be-test 는 `app/` / `alembic/` 미수정.

## 2. 컬럼 정본

```sql
ALTER TABLE league
  ADD COLUMN is_active boolean NOT NULL DEFAULT true;

CREATE INDEX league_active_idx
  ON league (is_active) WHERE is_active;
```

- `NOT NULL DEFAULT true` 이므로 기존 row 는 백필 스크립트 없이도 즉시 `true` 로 채워진다 (Postgres 가 ADD COLUMN ... DEFAULT 를 메타데이터-only 로 처리).
- partial index 는 `WHERE is_active` 조건. 비활성 league 수가 많아질 미래 시점에 daily-sync 쿼리의 인덱스 활용을 보장.

## 3. 마이그레이션 메타데이터

| 항목 | 값 |
|---|---|
| `revision` | `0002_league_is_active` |
| `down_revision` | `"0001_initial_schema"` |
| `branch_labels` | `None` |
| `depends_on` | `None` |

### 3.1 upgrade()

1. `op.add_column("league", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))`
2. `op.create_index("league_active_idx", "league", ["is_active"], postgresql_where=sa.text("is_active"))`

> **참고**: `server_default=sa.true()` 가 백필을 자동으로 처리. 마이그레이션 적용 후 server_default 를 제거할 필요는 없음 (db-schema.md 정본이 DEFAULT true 를 명시).

### 3.2 downgrade()

1. `op.drop_index("league_active_idx", table_name="league")`
2. `op.drop_column("league", "is_active")`

생성 역순으로 정확히 되돌릴 것.

## 4. 모델 변경 (be-dev 영역)

`app/models/league.py` (또는 entity 가 정의된 모듈) 의 `League` 클래스에:

```python
is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.true())
```

본 spec 단계 단위 테스트는 모델에 `is_active` 가 `bool` / NOT NULL / server_default 로 정의되어 있는지를 메타데이터 introspection 으로 검증한다.

## 5. 호환성

- **2-step 패턴 불필요**: ADD COLUMN with NOT NULL DEFAULT 는 Postgres 11+ 에서 즉시 안전 (table rewrite 없음).
- 기존 코드 (daily-sync) 가 컬럼을 모르더라도 INSERT/UPDATE 시 영향 없음 (DEFAULT 자동 적용).
- ADMIN endpoint 로 토글하는 동작 (UPDATE league SET is_active=false WHERE ...) 은 본 task 범위 밖.

## 6. 에러 케이스 / 비즈니스 규칙

- `is_active` NULL 로 INSERT 시도 → NOT NULL 위반
- partial index 는 `is_active=true` 인 row 만 색인 — false row 가 늘어나도 인덱스가 비대해지지 않는다
- 5리그 시드는 모두 `is_active=true` (시드 스크립트는 본 task 외)

## 7. DB 의존성 / 통합 테스트 정책

- 통합 테스트 fixture 는 격리 schema 에 마이그레이션 **base → head** 적용. 즉 `0001_initial_schema` → `0002_league_is_active` 순서로 두 마이그레이션 다 적용된 상태에서 검증.
- prod schema (public) 접근 금지. 통합은 격리 schema 안에서만.

## 8. 인증 요구사항

본 task 는 endpoint 가 아니므로 인증 N/A. (단, 향후 `PATCH /api/v1/admin/leagues/:id/active` 같은 endpoint 가 ADMIN role 게이트 뒤에 만들어질 예정 — 별도 task.)

## 9. 변경 기록

| 날짜 | 변경 |
|---|---|
| 2026-05-13 | spec 작성 (be-test, L1 follow-up). db-schema.md §3.1 mirror |
