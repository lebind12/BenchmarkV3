# DB Schema — Postgres (Supabase)

본 문서는 데이터베이스 스키마의 정본 (SSOT) 이다. SQLAlchemy 모델과 alembic 마이그레이션은 항상 본 문서와 동기 상태를 유지한다.

상위 결정:
- 도메인 / 데이터 정책: `@CLAUDE.md`
- 워커 운영: `@docs/workers/`
- 작업 정본: `@Plans.md`

---

## 1. 전체 테이블 (13개)

| # | 테이블 | 역할 |
|---|---|---|
| 1 | `league` | 5리그 메타 |
| 2 | `league_translation` | 리그 한글표기 (1:1) |
| 3 | `venue` | 경기장 |
| 4 | `team` | 팀 메타 |
| 5 | `team_translation` | 팀 한글표기 (1:1) |
| 6 | `team_season` | 팀-리그-시즌 정션 (M:N) |
| 7 | `player` | 선수 메타 (현 소속 denorm) |
| 8 | `player_translation` | 선수 한글표기 (1:1) |
| 9 | `player_season_stat` | 선수 시즌 스탯 (하이브리드: 핵심 컬럼 + raw JSONB) |
| 10 | `fixture` | 경기 |
| 11 | `fixture_detail` | events/statistics/lineups JSONB |
| 12 | `standings` | 순위표 |
| 13 | `app_user` | 사용자 (인증) |

---

## 2. ER 관계

```
league (5리그)
  ├─ 1:0..1 ─ league_translation
  ├─ 1:N    ─ team_season ─ N:1 ─ team
  ├─ 1:N    ─ fixture
  ├─ 1:N    ─ player_season_stat
  └─ 1:N    ─ standings

team
  ├─ 1:0..1 ─ team_translation
  ├─ N:1    ─ venue (home)
  ├─ 1:N    ─ player (current_team_id, nullable)
  ├─ 1:N    ─ fixture (home_team_id / away_team_id, nullable for cup draws)
  ├─ 1:N    ─ player_season_stat
  └─ 1:N    ─ standings

venue
  ├─ 1:N ─ team (home)
  └─ 1:N ─ fixture

player
  ├─ 1:0..1 ─ player_translation
  ├─ N:1    ─ team (current_team_id)
  └─ 1:N    ─ player_season_stat

fixture
  ├─ 1:0..1 ─ fixture_detail
  └─ N:1    ─ league, home_team, away_team, venue

app_user  (독립)
```

---

## 3. DDL

### 3.1 `league`

```sql
CREATE TABLE league (
    id             bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id    integer     NOT NULL UNIQUE,         -- API-Football league.id
    name           text        NOT NULL,
    type           text        NOT NULL,                -- 'League' | 'Cup'
    logo_url       text,
    country_name   text,                                 -- API country.name
    country_code   text,                                 -- API country.code
    country_flag   text,                                 -- API country.flag
    slug           text        NOT NULL UNIQUE,
    current_season integer,                              -- 현재 진행 시즌 (예: 2024)
    is_active      boolean     NOT NULL DEFAULT true,    -- daily-sync 적재 대상 여부. ADMIN 이 토글
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT league_type_check CHECK (type IN ('League', 'Cup'))
);
CREATE INDEX league_type_idx ON league (type);
CREATE INDEX league_active_idx ON league (is_active) WHERE is_active;
```

`is_active`: daily-sync 워커가 매 사이클 `WHERE is_active = true` 인 league 만 sync. ADMIN endpoint 로 동적 추가/제외. 초기 5리그 시드 시 모두 `is_active=true`.

**시드 매핑 (5리그)**:

| external_id | name | type | slug |
|---|---|---|---|
| 39 | Premier League | League | `premier-league` |
| 2 | UEFA Champions League | Cup | `champions-league` |
| 3 | UEFA Europa League | Cup | `europa-league` |
| 48 | League Cup (Carabao) | Cup | `carabao-cup` |
| 45 | FA Cup | Cup | `fa-cup` |

### 3.2 `league_translation`

```sql
CREATE TABLE league_translation (
    league_id     bigint      NOT NULL PRIMARY KEY
                              REFERENCES league(id) ON DELETE CASCADE,
    name_ko       text,                                  -- NULL = 일시 미번역 (새 리그 추가 시점)
    short_name_ko text,
    updated_at    timestamptz NOT NULL DEFAULT now()
);
```

### 3.3 `venue`

```sql
CREATE TABLE venue (
    id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id   integer     UNIQUE,                  -- nullable (일부 fixture venue 는 ID 없음)
    name          text        NOT NULL,
    city          text,
    country       text,
    capacity      integer,
    surface       text,                                 -- 'grass' 등
    address       text,
    image_url     text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
```

### 3.4 `team`

```sql
CREATE TABLE team (
    id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id   integer     NOT NULL UNIQUE,
    name          text        NOT NULL,
    code          text,                                  -- 영문 3-letter 약칭 (예: 'MUN')
    country       text,
    founded       integer,
    is_national   boolean     NOT NULL DEFAULT false,
    logo_url      text,
    venue_id      bigint      REFERENCES venue(id) ON DELETE SET NULL,
    slug          text        NOT NULL UNIQUE,           -- '<slugify(name)>-<external_id>' 형식
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX team_country_idx ON team (country);
CREATE INDEX team_venue_idx   ON team (venue_id);
```

### 3.5 `team_translation`

```sql
CREATE TABLE team_translation (
    team_id       bigint      NOT NULL PRIMARY KEY
                              REFERENCES team(id) ON DELETE CASCADE,
    name_ko       text,
    short_name_ko text,
    updated_at    timestamptz NOT NULL DEFAULT now()
);
```

### 3.6 `team_season`

```sql
CREATE TABLE team_season (
    team_id      bigint      NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    league_id    bigint      NOT NULL REFERENCES league(id) ON DELETE CASCADE,
    season_year  integer     NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (team_id, league_id, season_year)
);
CREATE INDEX team_season_league_year_idx ON team_season (league_id, season_year);
```

### 3.7 `player`

```sql
CREATE TABLE player (
    id              bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id     integer     NOT NULL UNIQUE,
    name            text        NOT NULL,                -- API player.name (자주 약어 'S. Sherring')
    firstname       text,
    lastname        text,
    age             smallint,
    birth_date      date,
    birth_place     text,
    birth_country   text,
    nationality     text,
    height_cm       smallint,                             -- API '188 cm' 파싱
    weight_kg       smallint,                             -- API '78 kg' 파싱
    injured         boolean     NOT NULL DEFAULT false,
    photo_url       text,
    current_team_id bigint      REFERENCES team(id) ON DELETE SET NULL,
    slug            text        NOT NULL UNIQUE,           -- '<slugify(name)>-<external_id>'
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX player_team_idx        ON player (current_team_id);
CREATE INDEX player_nationality_idx ON player (nationality);
```

### 3.8 `player_translation`

```sql
CREATE TABLE player_translation (
    player_id     bigint      NOT NULL PRIMARY KEY
                              REFERENCES player(id) ON DELETE CASCADE,
    name_ko       text,
    short_name_ko text,
    updated_at    timestamptz NOT NULL DEFAULT now()
);
```

### 3.9 `player_season_stat`

```sql
CREATE TABLE player_season_stat (
    id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id     bigint      NOT NULL REFERENCES player(id) ON DELETE CASCADE,
    team_id       bigint      NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    league_id     bigint      NOT NULL REFERENCES league(id) ON DELETE CASCADE,
    season_year   integer     NOT NULL,

    -- 자주 표시되는 핵심 stats
    position      text,                              -- games.position
    shirt_number  smallint,                          -- games.number
    appearances   smallint,                          -- games.appearences (API typo)
    minutes       integer,                           -- games.minutes
    rating        numeric(4,2),                      -- games.rating ('7.130000' → 7.13)
    goals         smallint,                          -- goals.total
    assists       smallint,                          -- goals.assists
    yellow_cards  smallint,                          -- cards.yellow
    red_cards     smallint,                          -- cards.red

    -- 전체 stats raw
    raw_stats     jsonb       NOT NULL,

    updated_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT player_season_stat_uniq UNIQUE (player_id, team_id, league_id, season_year)
);
CREATE INDEX player_season_stat_player_idx    ON player_season_stat (player_id);
CREATE INDEX player_season_stat_team_year_idx ON player_season_stat (team_id, season_year);
-- 득점 랭킹용
CREATE INDEX player_season_stat_topscorer_idx ON player_season_stat (league_id, season_year, goals DESC);
```

### 3.10 `fixture`

```sql
CREATE TABLE fixture (
    id              bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id     integer     NOT NULL UNIQUE,
    league_id       bigint      NOT NULL REFERENCES league(id) ON DELETE CASCADE,
    season_year     integer     NOT NULL,
    round           text,                                 -- 'Regular Season - 1', 'Round of 16' 등

    home_team_id    bigint      REFERENCES team(id) ON DELETE SET NULL,    -- 컵 추첨 미정 시 NULL
    away_team_id    bigint      REFERENCES team(id) ON DELETE SET NULL,
    venue_id        bigint      REFERENCES venue(id) ON DELETE SET NULL,
    referee         text,
    timezone        text,
    kickoff_at      timestamptz NOT NULL,                  -- API fixture.date
    timestamp_unix  bigint,

    status_long     text,
    status_short    text        NOT NULL,                  -- 'FT', 'NS', '1H', 'HT', '2H', 'ET', 'P', 'CANC', ...
    status_elapsed  smallint,
    period_first    bigint,
    period_second   bigint,

    goals_home      smallint,                              -- 경기 시작 전 NULL
    goals_away      smallint,
    score_ht_home   smallint,                              -- halftime
    score_ht_away   smallint,
    score_ft_home   smallint,                              -- fulltime
    score_ft_away   smallint,
    score_et_home   smallint,                              -- extratime
    score_et_away   smallint,
    score_pen_home  smallint,                              -- penalty
    score_pen_away  smallint,
    home_winner     boolean,                               -- 종료 전 NULL
    away_winner     boolean,

    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX fixture_league_season_idx ON fixture (league_id, season_year);
CREATE INDEX fixture_kickoff_idx       ON fixture (kickoff_at);
CREATE INDEX fixture_status_idx        ON fixture (status_short);
CREATE INDEX fixture_home_team_idx     ON fixture (home_team_id);
CREATE INDEX fixture_away_team_idx     ON fixture (away_team_id);
```

### 3.11 `fixture_detail`

```sql
CREATE TABLE fixture_detail (
    fixture_id   bigint      NOT NULL PRIMARY KEY REFERENCES fixture(id) ON DELETE CASCADE,
    events       jsonb,                       -- /fixtures/events 응답
    statistics   jsonb,                       -- /fixtures/statistics 응답
    lineups      jsonb,                       -- /fixtures/lineups 응답
    fetched_at   timestamptz,                 -- 마지막 API fetch 시각
    updated_at   timestamptz NOT NULL DEFAULT now()
);
```

### 3.12 `standings`

```sql
CREATE TABLE standings (
    id                  bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    league_id           bigint      NOT NULL REFERENCES league(id) ON DELETE CASCADE,
    season_year         integer     NOT NULL,
    team_id             bigint      NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    group_name          text,                              -- UCL/UEL 'Group A' 등. 리그면 NULL

    rank                smallint    NOT NULL,
    points              smallint    NOT NULL,
    played              smallint    NOT NULL,
    win                 smallint    NOT NULL,
    draw                smallint    NOT NULL,
    loss                smallint    NOT NULL,
    goals_for           smallint    NOT NULL,
    goals_against       smallint    NOT NULL,
    goals_diff          smallint,
    form                text,                              -- 'WWDLW' 등
    status              text,                              -- 'same', 'up' 등
    description         text,                              -- 'Promotion - Champions League' 등

    home_away_breakdown jsonb,                              -- {home: {...}, away: {...}}
    raw_data            jsonb,

    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- group_name NULL 도 unique 처리
CREATE UNIQUE INDEX standings_uniq
    ON standings (league_id, season_year, team_id, COALESCE(group_name, ''));

CREATE INDEX standings_league_season_rank_idx
    ON standings (league_id, season_year, rank);
```

### 3.13 `app_user`

```sql
CREATE TABLE app_user (
    id              bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           text        NOT NULL UNIQUE,
    password_hash   text        NOT NULL,                  -- bcrypt or argon2
    role            text        NOT NULL DEFAULT 'USER',
    nickname        text,
    is_active       boolean     NOT NULL DEFAULT true,
    email_verified  boolean     NOT NULL DEFAULT false,
    last_login_at   timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT app_user_role_check CHECK (role IN ('USER', 'STREAMER', 'ADMIN'))
);
CREATE INDEX app_user_role_idx ON app_user (role);
```

---

## 4. ON DELETE 정책 일람

| FROM → TO | ON DELETE | 의미 |
|---|---|---|
| `*_translation.<entity>_id → <entity>.id` | CASCADE | entity 삭제 시 번역도 같이 |
| `team.venue_id → venue.id` | SET NULL | venue 삭제 시 team 의 홈 venue 만 NULL |
| `team_season.{team_id, league_id} → ...` | CASCADE | 정션이라 삭제 시 row 제거 |
| `player.current_team_id → team.id` | SET NULL | 팀 삭제 시 선수의 current 만 NULL (선수 자체는 유지) |
| `player_season_stat.* → ...` | CASCADE | 스탯은 부모 사라지면 의미 없음 |
| `fixture.league_id → league.id` | CASCADE | 리그 사라지면 fixture 도 |
| `fixture.{home_team_id, away_team_id, venue_id}` | SET NULL | fixture 자체는 살림 |
| `fixture_detail.fixture_id → fixture.id` | CASCADE | detail 은 fixture 종속 |
| `standings.* → ...` | CASCADE | 부모 사라지면 의미 없음 |

---

## 5. NULL 허용 핵심 컬럼

| 컬럼 | NULL 의미 |
|---|---|
| `*_translation.name_ko / short_name_ko` | 번역 대기 상태 (translation-filler 가 채울 예정) |
| `fixture.home_team_id / away_team_id` | 컵 추첨 미정 라운드. 추첨 결과 나오면 UPDATE |
| `fixture.goals_*, score_*` | 경기 시작 전 |
| `fixture.home_winner / away_winner` | 종료 전 |
| `fixture.referee, timezone` | API 응답에 없을 수도 |
| `team.venue_id` | venue 정보 없거나 미발견 |
| `player.current_team_id` | 무소속 또는 미파악 |
| `venue.external_id` | API 가 venue ID 없이 name 만 주는 경우 |

---

## 6. 시즌 처리

- 별도 `season` 테이블 없음 (제거됨)
- `league.current_season int` 가 "각 리그의 현재 시즌이 어느 year 인가" 단일 소스
- `fixture / team_season / player_season_stat / standings` 에 `season_year int` 컬럼
- CLAUDE.md §3 "최신 2시즌 보관" 정책은 워커 책임 (오래된 시즌 row 정기 삭제)

---

## 7. 인덱스 / 제약 일람

| 테이블 | UNIQUE / PRIMARY 핵심 |
|---|---|
| 모든 entity 테이블 | `external_id` UNIQUE (upsert key) |
| `*_translation` | PK = FK (1:1 강제) |
| `team_season` | composite PK (team_id, league_id, season_year) |
| `player_season_stat` | UNIQUE (player_id, team_id, league_id, season_year) |
| `standings` | UNIQUE (league_id, season_year, team_id, COALESCE(group_name, '')) |
| `app_user` | UNIQUE email |

| 자주 쓰는 인덱스 |
|---|
| `fixture (league_id, season_year)` — 시즌 fixture 조회 |
| `fixture (kickoff_at)` — 가까운 경기 |
| `fixture (status_short)` — 라이브/예정/종료 필터 |
| `player_season_stat (league_id, season_year, goals DESC)` — 득점왕 |
| `standings (league_id, season_year, rank)` — 순위표 |

---

## 8. daily-sync 적재 순서 (개요)

큐(B) 후보 산정 후 다음 순서로 처리:

1. league (5리그 메타, 항상 풀 sync — 5 calls)
2. team (큐 대상 fixture 의 home/away 팀 + 5리그 current_season 의 team_season 멤버)
3. venue (위 team 들의 home venue)
4. player (큐 대상 team 의 squad)
5. team_season (위 (league, season, team) 관계)
6. fixture (큐 대상)
7. fixture_detail (위 fixture 의 events/statistics/lineups)
8. standings (5리그 × current_season)
9. player_season_stat (위 player 의 시즌 스탯)
10. league_translation / team_translation / player_translation: daily-sync 가 새 entity 발견 시 INSERT ON CONFLICT DO NOTHING (한글 NULL row 생성)

전체 덮어쓰기 (entity 테이블) + INSERT ONLY (번역 테이블) 정책 적용.

세부 적재 알고리즘은 `docs/workers/daily-sync.md` 에서.

---

## 9. 변경 기록

| 날짜 | 변경 |
|---|---|
| 2026-05-13 | 초기 스키마 13 테이블 합의 (메인 세션) |
| 2026-05-13 | `league.is_active` 컬럼 추가 — ADMIN 이 동적으로 수집 league 추가/제외 가능 (월드컵/유로 등 추후 추가 시나리오) |
