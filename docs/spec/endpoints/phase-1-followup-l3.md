# Phase 1 Follow-up L3 — `h2h_fixture` 테이블 추가

본 문서는 BE 워크플로 spec 산출물이며, **additive DB migration** 의 요구사항 mirror 다.
정본은 `docs/spec/db-schema.md` §3.17.

> ⚠️ **불변 원칙**
> - 본 task 는 `h2h_fixture` 1 테이블 + 함수 인덱스 추가하는 **단일 마이그레이션 (0004)** 만 생성
> - 기존 `0001_initial_schema.py`, `0002_league_is_active.py`, `0003_transfer_injury_news.py` **절대 수정 금지**
> - 컬럼/인덱스/제약 정본 §3.17 과 1:1 일치

## 1. 의존성 (선행 task)

- **L2 (`0003_transfer_injury_news`) 머지 완료 후** 작업 가능. 본 task 의 마이그레이션 `down_revision = "0003_transfer_injury_news"` (L2 의 revision id 와 정확히 일치).
- L2 가 아직 머지 안 됐다면 dev 는 L2 머지 후 rebase 한 뒤 0004 작성.

## 2. 마이그레이션 메타데이터

| 항목 | 값 |
|---|---|
| `revision` | `0004_h2h_fixture` |
| `down_revision` | `"0003_transfer_injury_news"` |
| `branch_labels` | `None` |
| `depends_on` | `None` |

## 3. 테이블 정본 (§3.17)

```sql
CREATE TABLE h2h_fixture (
    id                 bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id        integer     NOT NULL UNIQUE,
    home_team_id       bigint      NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    away_team_id       bigint      NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    league_external_id integer,
    league_name        text,
    season_year        integer,
    kickoff_at         timestamptz NOT NULL,
    status_short       text,
    goals_home         smallint,
    goals_away         smallint,
    raw_data           jsonb,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- 두 팀 짝 조회용 함수 인덱스 (순서 무관)
CREATE INDEX h2h_pair_idx ON h2h_fixture
    (LEAST(home_team_id, away_team_id), GREATEST(home_team_id, away_team_id), kickoff_at DESC);
```

### 컬럼 의미

| 컬럼 | 비고 |
|---|---|
| `external_id` | API-Football fixture.id. UNIQUE — upsert key |
| `home_team_id`, `away_team_id` | team FK CASCADE. **양 팀 모두 DB 존재 필수**. 한쪽이 외부 팀 (5리그 외 DB 미적재) 이면 적재 skip |
| `league_external_id` | 5리그 외 대회 (Friendlies 등) 포함. FK 없음 (5리그 화이트리스트 외라 league 테이블에 row 없을 수 있음). nullable |
| `league_name` | API league.name 그대로 ('Friendlies', 'Premier League' 등). 표기 용 |
| `season_year` | nullable. 친선전 등 시즌 무관 시 NULL |
| `kickoff_at` | NOT NULL |
| `status_short` | API status.short ('FT', 'CANC' 등). nullable |
| `goals_home`, `goals_away` | smallint nullable (경기 종료 전 또는 미진행 시 NULL) |
| `raw_data` | API 응답 원본 보관 JSONB |

### 함수 인덱스 `h2h_pair_idx`

순서 무관한 팀 짝 조회 최적화. 쿼리 패턴:
```sql
SELECT * FROM h2h_fixture
WHERE LEAST(home_team_id, away_team_id)    = LEAST($1, $2)
  AND GREATEST(home_team_id, away_team_id) = GREATEST($1, $2)
ORDER BY kickoff_at DESC
LIMIT 5;
```

(home=A, away=B) 와 (home=B, away=A) 가 같은 그룹으로 묶임. 인덱스가 이 쿼리에 정확히 매칭.

## 4. ON DELETE 정책

| FROM → TO | ON DELETE |
|---|---|
| `h2h_fixture.home_team_id → team.id` | CASCADE |
| `h2h_fixture.away_team_id → team.id` | CASCADE |

## 5. upgrade() / downgrade()

### upgrade()
1. `op.create_table("h2h_fixture", ...)` (UNIQUE external_id, 두 FK CASCADE)
2. `op.execute("CREATE INDEX h2h_pair_idx ON h2h_fixture (LEAST(home_team_id, away_team_id), GREATEST(home_team_id, away_team_id), kickoff_at DESC)")` — 함수 인덱스는 alembic 의 `create_index` 만으로는 표현 어렵기 때문에 raw SQL 권장. SQLAlchemy 측 모델 인덱스도 동일 SQL 표현식으로 선언 (`Index("h2h_pair_idx", func.least(...), func.greatest(...), col.desc())`).

### downgrade()
1. `op.execute("DROP INDEX IF EXISTS h2h_pair_idx")`
2. `op.drop_table("h2h_fixture")`

## 6. 모델 (be-dev 영역)

`app/models/h2h_fixture.py` 추가 + `app/models/__init__.py` export. SQLAlchemy 함수 인덱스 선언:

```python
from sqlalchemy import Index, func
Index(
    "h2h_pair_idx",
    func.least(HF.home_team_id, HF.away_team_id),
    func.greatest(HF.home_team_id, HF.away_team_id),
    HF.kickoff_at.desc(),
)
```

## 7. 테이블 개수

- L2 (0003) 적용 후: 16 테이블
- **L3 (0004) 적용 후: 17 테이블** (+ h2h_fixture)

## 8. 비기능

- 본 task 는 적재 워커 코드 (daily-sync Step 7c) 를 포함하지 않음 — W2 / 별도 task 가 담당
- 본 task 는 schema + 모델 + 마이그레이션 + 테스트만

## 9. 변경 기록

| 날짜 | 변경 |
|---|---|
| 2026-05-14 | spec 작성 (be-test, L3). db-schema.md §3.17 mirror. L2 (0003) 머지 의존 |
