---
feature_id: main-home
phase: mock
author: fe-planner
created: 2026-05-14
---

# main-home — 개발 방향 (devplan)

대상: fe-dev. 본 문서는 컴포넌트 트리 / Pinia store / MSW handler / shadcn-vue 의존 / 새 endpoint 후보를 정의한다.

---

## 1. 라우팅

- vue-router `frontend/src/router/index.ts` 의 root route 에 추가:
  - path: `/`
  - name: `home`
  - component: `() => import('@/views/HomeView.vue')`
  - meta: `{ layout: 'default', title: '홈' }`
- 본 feature 가 `App.vue` 의 `RouterView` 위에 전역 header(56px) 를 렌더링하는 `DefaultLayout.vue` 를 생성/사용한다 (다른 feature 와 공유될 layout 이므로 본 feature 가 최초 작성).

---

## 2. 디렉토리 / 파일 배치

```
frontend/src/
├── views/
│   └── HomeView.vue                       # 라우트 진입점 (3패널 grid 컨테이너)
├── layouts/
│   └── DefaultLayout.vue                  # 56px 헤더 + <RouterView />
├── components/
│   ├── common/
│   │   ├── AppHeader.vue                  # 전역 상단 탭 (56px)
│   │   ├── ThemeToggle.vue                # 다크/라이트 토글
│   │   ├── AuthToggle.vue                 # 로그인 / 프로필 토글
│   │   ├── PanelScroll.vue                # hidden-scrollbar + fade-out gradient
│   │   ├── EmptyState.vue                 # 빈 상태 공용 (아이콘 + 카피 + action slot)
│   │   ├── ErrorState.vue                 # 에러 상태 공용 ("다시 시도")
│   │   └── SkeletonCard.vue               # 스켈레톤 카드 공용
│   └── home/
│       ├── LeftPanel.vue                  # 25% 좌측 컨테이너 (로고 30% + 큐브 70%)
│       ├── SiteLogo.vue                   # 로고
│       ├── CubeCarousel.vue               # 3D 큐브 (회전 / dot / 키보드)
│       ├── faces/
│       │   ├── CubeNewsFace.vue
│       │   ├── CubeHotPlayerFace.vue
│       │   ├── CubeTransferFace.vue
│       │   └── CubeInjuryFace.vue
│       ├── CenterPanel.vue                # 중앙 50% (필터 + 리스트)
│       ├── FixtureFilters.vue             # 리그 탭 + 기간 토글
│       ├── FixtureList.vue                # 카드 리스트 + 상태
│       ├── FixtureCard.vue                # 1 경기 카드
│       ├── RightPanel.vue                 # 우측 25% (위/아래 50%)
│       ├── StandingsBlock.vue             # 우측 상단
│       ├── StandingsRow.vue
│       ├── TopPlayersBlock.vue            # 우측 하단
│       └── TopPlayerRow.vue
├── stores/
│   ├── home.ts                            # 홈 전용 Pinia store
│   └── auth.ts                            # (이미 있을 수도) mock role 분기
├── lib/
│   ├── api/home.ts                        # fetch wrapper
│   ├── format/datetime.ts                 # KST / 상대시간 유틸
│   └── league-colors.ts                   # slug → CSS var (palette doc §9)
├── styles/
│   └── leagues.css                        # league-palette.md §8 그대로
├── mocks/
│   ├── handlers/home.ts                   # MSW handler (본 feature)
│   └── data/home/*.json                   # mock JSON (각 endpoint 별)
└── types/
    └── home.ts                            # 본 feature TS 타입
```

shadcn-vue 컴포넌트 (이미 설치 가정 / 없으면 fe-dev 가 추가):
- `Tabs`, `ToggleGroup`, `Select`, `Skeleton`, `Card`, `Badge`, `Button`, `DropdownMenu`

---

## 3. 컴포넌트 트리 (런타임)

```
DefaultLayout
└── AppHeader  (56px)
    ├── SiteLogoMini
    ├── NavTabs (홈/경기/순위/팀/선수/스탯/(방송))
    └── 우측: ThemeToggle + AuthToggle
└── HomeView   (height: calc(100vh - 56px); grid 25/50/25)
    ├── LeftPanel
    │   ├── SiteLogo (30%)
    │   └── CubeCarousel (70%)
    │       ├── CubeNewsFace
    │       ├── CubeHotPlayerFace
    │       ├── CubeTransferFace
    │       └── CubeInjuryFace
    │       └── DotIndicator (footer of cube)
    ├── CenterPanel
    │   ├── FixtureFilters
    │   └── PanelScroll
    │       └── FixtureList
    │           └── FixtureCard * N
    └── RightPanel
        ├── StandingsBlock (50%)
        │   ├── LeagueSelect
        │   └── PanelScroll → StandingsRow * N
        └── TopPlayersBlock (50%)
            ├── MetricSelect + LeagueSelect
            └── PanelScroll → TopPlayerRow * N
```

---

## 4. Pinia store — `useHomeStore`

```ts
// stores/home.ts
interface HomeState {
  cube: {
    activeFace: 0 | 1 | 2 | 3
    autoRotate: boolean          // hover/focus 시 false
    paused: boolean
    timerHandle: number | null
  }
  news:      AsyncSlice<NewsItem[]>
  hot:       AsyncSlice<HotPlayer[]>
  transfers: AsyncSlice<Transfer[]>
  injuries:  AsyncSlice<Injury[]>

  fixtures: {
    filter: { league_id: number | null; period: 'day' | 'week' | 'month' }
    data:   AsyncSlice<FixtureSummary[]>
  }

  standings: {
    league_id: number             // 기본 39 (EPL)
    data: AsyncSlice<StandingRow[]>
  }
  topPlayers: {
    league_id: number             // 기본 39
    metric: 'goals' | 'assists' | 'yellow_cards' | 'red_cards'
    data: AsyncSlice<TopPlayerRow[]>
  }
}

type AsyncSlice<T> = {
  status: 'idle' | 'loading' | 'ok' | 'error'
  value: T | null
  error: string | null
  fetchedAt: number | null
}
```

Actions:
- `bootstrap()` — 페이지 mount 시 모든 fetch 병렬 트리거
- `fetchCubeFace(face)` / `fetchFixtures()` / `fetchStandings()` / `fetchTopPlayers()`
- `setLeagueFilter(id)` / `setPeriod(p)` → 즉시 `fetchFixtures()` 호출
- `setStandingsLeague(id)` / `setTopPlayersLeague(id)` / `setTopPlayersMetric(m)`
- `nextFace()` / `setFace(i)` / `pauseAutoRotate()` / `resumeAutoRotate()`
- `retryPanel('news' | 'fixtures' | ...)` — 에러 패널 재시도

자동 회전 timer: `bootstrap` 에서 `setInterval(nextFace, 10000)` 시작. hover/focus 시 `pauseAutoRotate()` → `clearInterval`. 재개 시 다시 setInterval.

---

## 5. MSW handler 목록 (본 feature 가 만드는 mock)

`frontend/src/mocks/handlers/home.ts`:

```ts
import { http, HttpResponse } from 'msw'
import news from '@/mocks/data/home/news.json'
import hot from '@/mocks/data/home/hot.json'
import transfers from '@/mocks/data/home/transfers.json'
import injuries from '@/mocks/data/home/injuries.json'
import fixturesAll from '@/mocks/data/home/fixtures.json'
import standingsEpl from '@/mocks/data/home/standings.epl.json'
// ... 5리그 분
import topGoalsEpl from '@/mocks/data/home/top.goals.epl.json'
// ... metric × league

export const homeHandlers = [
  http.get('/api/v1/home/news',         () => HttpResponse.json(news)),
  http.get('/api/v1/home/hot-players',  () => HttpResponse.json(hot)),
  http.get('/api/v1/home/transfers',    () => HttpResponse.json(transfers)),
  http.get('/api/v1/home/injuries',     () => HttpResponse.json(injuries)),

  http.get('/api/v1/home/fixtures', ({ request }) => {
    const url = new URL(request.url)
    const league = url.searchParams.get('league_id')
    const period = url.searchParams.get('period') ?? 'day'
    return HttpResponse.json(filterFixtures(fixturesAll, league, period))
  }),

  http.get('/api/v1/home/standings', ({ request }) => {
    const id = new URL(request.url).searchParams.get('league_id')
    return HttpResponse.json(pickStandings(id))
  }),

  http.get('/api/v1/home/top-players', ({ request }) => {
    const u = new URL(request.url).searchParams
    return HttpResponse.json(pickTop(u.get('league_id'), u.get('metric')))
  }),
]
```

Mock JSON 시드 데이터 가이드 (fe-dev 가 생성):
- fixtures: 오늘 / 이번주 / 이번달 각 3~12 건. status NS/FT 혼합 1건 PST 포함 (빈 카드 케이스 검증용)
- standings: EPL 20팀 + UCL 32팀 (시즌 휴식기 시뮬용 빈 응답 케이스 1개 fixtures.empty.json 별도)
- top players: 각 리그 × 4 metric = 20 파일, 30 row
- news/hot/transfer/injury: 정확 5건 (정상) + `empty: true` 케이스 1개 (빈 상태 검증)

---

## 6. TypeScript 타입 (응답 shape SSOT)

`frontend/src/types/home.ts`:

```ts
export interface LeagueRef {
  external_id: number             // 39, 2, 3, 48, 45
  slug: 'premier-league'|'champions-league'|'europa-league'|'carabao-cup'|'fa-cup'
  name_ko: string | null
  short_name_ko: string | null
  name: string                    // 영문 fallback
}

export interface TeamRef {
  external_id: number
  slug: string
  name_ko: string | null
  short_name_ko: string | null
  name: string
  logo_url: string | null
}

export interface PlayerRef {
  external_id: number
  slug: string
  name_ko: string | null
  name: string
  photo_url: string | null
  team: Pick<TeamRef, 'external_id'|'slug'|'name_ko'|'name'|'logo_url'>
  league: Pick<LeagueRef, 'external_id'|'slug'|'name_ko'|'name'>
}

export interface NewsItem {
  id: string
  title_ko: string | null
  title: string                   // 원문 fallback
  summary_ko: string | null
  source: string                  // 도메인 (예: "bbc.com")
  url: string                     // 외부 원문
  thumbnail_url: string | null
  published_at: string            // ISO8601 UTC
}

export interface HotPlayer {
  player: PlayerRef
  goals: number
  assists: number
  score: number                   // goals + assists (BE 가 계산)
}

export interface Transfer {
  id: string
  player: PlayerRef
  from_team: TeamRef
  to_team: TeamRef
  transfer_date: string           // ISO date
  fee: string | null              // "€60m" 같은 표기 (있을 때)
}

export interface Injury {
  id: string
  player: PlayerRef
  injury_type: string             // "Hamstring" 등
  expected_return: string | null  // ISO date (있을 때)
  reported_at: string             // ISO date
}

export interface FixtureSummary {
  external_id: number
  league: LeagueRef
  home: TeamRef
  away: TeamRef
  kickoff_at: string              // ISO8601 UTC
  status_short: 'NS'|'1H'|'HT'|'2H'|'ET'|'PEN'|'FT'|'AET'|'PST'|'CANC'
  goals_home: number | null
  goals_away: number | null
}

export interface StandingRow {
  rank: number
  team: TeamRef
  points: number
  played: number
  win: number
  draw: number
  loss: number
  goals_for: number
  goals_against: number
}

export interface TopPlayerRow {
  rank: number
  player: PlayerRef
  metric_value: number
}
```

→ Integration 단계에서 동일 shape 를 **zod** 스키마로 보호 (fe-workflow §9).

---

## 7. 새 endpoint 후보 (BE 에 신호)

본 feature 가 mock 으로 사용하는 endpoint = 추후 BE 가 구현해야 할 후보. fe-dev 가 mock 머지 직후 `frontend/endpoint-requests/<id>.request.json` 으로 자동 생성한다 (fe-workflow §6).

| endpoint id | path / method | 비고 |
|---|---|---|
| `GET__api_v1_home_news` | `GET /api/v1/home/news` | EPL 키워드 매칭 최신 5건. `news_article` 테이블 |
| `GET__api_v1_home_hot_players` | `GET /api/v1/home/hot-players` | 5리그 통합 골+어시 top 5. `player_season_stat` |
| `GET__api_v1_home_transfers` | `GET /api/v1/home/transfers` | 최근 5건. `transfer` 테이블 (BE 가 신규 추가 필요할 수 있음) |
| `GET__api_v1_home_injuries` | `GET /api/v1/home/injuries` | 곧 경기 영향 5건. `injury` 테이블 |
| `GET__api_v1_home_fixtures` | `GET /api/v1/home/fixtures?league_id&period` | period ∈ day/week/month, KST 기준 |
| `GET__api_v1_home_standings` | `GET /api/v1/home/standings?league_id` | 현재 시즌 standings |
| `GET__api_v1_home_top_players` | `GET /api/v1/home/top-players?league_id&metric` | metric ∈ goals/assists/yellow_cards/red_cards |

⚠ `transfer` / `injury` 테이블이 CLAUDE.md 의 `daily-sync` 책임에 명시되어 있으나 (CLAUDE.md §4 "transfers / injuries 적재"), 실제 테이블/마이그레이션 존재 여부는 BE 가 확인해야 함. devplan 으로 신호.

---

## 8. CSS 변수 / 색상 적용

- `frontend/src/styles/leagues.css` 를 `main.ts` 에서 import (league-palette.md §8 그대로 복사)
- league_id → slug 매핑 유틸 (`lib/league-colors.ts`):
  ```ts
  const ID_TO_SLUG: Record<number, string> = {
    39: 'premier-league',
    2:  'champions-league',
    3:  'europa-league',
    48: 'carabao-cup',
    45: 'fa-cup',
  }
  export function leagueVar(externalId: number, kind: 'primary'|'secondary'|'accent'|'on-primary') {
    const slug = ID_TO_SLUG[externalId]
    if (!slug) return 'var(--muted)'
    return `var(--league-${LEAGUE_TOKEN[slug]}-${kind})`
  }
  ```
- 리그 배지 컴포넌트 (`<LeagueBadge :league-id="..."/>`) 는 `--league-*-primary` 배경 + `--league-*-on-primary` 텍스트

---

## 9. 큐브 3D 구현 노트

```css
.cube-stage  { perspective: 1000px; height: 70%; }
.cube        { position: relative; width: 100%; height: 100%; transform-style: preserve-3d;
               transition: transform 0.8s cubic-bezier(.65,.05,.36,1); }
.cube.face-0 { transform: rotateY(0deg);    }
.cube.face-1 { transform: rotateY(-90deg);  }
.cube.face-2 { transform: rotateY(-180deg); }
.cube.face-3 { transform: rotateY(-270deg); }

.face { position: absolute; inset: 0; backface-visibility: hidden;
        transform: rotateY(var(--face-rot)) translateZ(var(--face-z)); }
.face-0 { --face-rot:   0deg; }
.face-1 { --face-rot:  90deg; }
.face-2 { --face-rot: 180deg; }
.face-3 { --face-rot: 270deg; }
/* --face-z = half of width. JS 가 ResizeObserver 로 계산 */
```

면 폭 변화 (반응형) 대응: `ResizeObserver` 로 컨테이너 width 측정 → `--face-z = width / 2` 동적 설정.

비활성 면 `aria-hidden="true"` + `inert` (focus 들어가지 않음).

---

## 10. 접근성 체크리스트

- [ ] 큐브 컨테이너 `role="region" aria-roledescription="carousel" aria-label="홈 큐브"`
- [ ] 각 면 `role="group" aria-roledescription="slide" aria-label="뉴스/핫/이적/부상"`
- [ ] dot 인디케이터 `role="tablist"` + 각 dot `role="tab" aria-selected`
- [ ] 클릭 가능 row 모두 `<button>` 또는 `<a>` + focus outline
- [ ] 색 대비 4.5:1 (palette doc §10 의 미해결 항목, fe-dev 시각 검증)
- [ ] 키보드 만으로 모든 패널 진입/이동 가능

---

## 11. 빌드 / 번들

- 큐브 면 4개 컴포넌트는 정적 import (lazy 안 함 — 작은 카드)
- `HomeView` 자체는 라우트 lazy
- 이미지 (선수 사진 / 팀 로고) `loading="lazy"` + width/height 지정 (CLS 방지)
- 번들 baseline 측정 후 ≥ 10% 회귀 시 fe-reviewer 알림

---

## 12. fe-dev 작업 순서 제안

1. DefaultLayout + AppHeader (전역, 다른 feature 가 의존)
2. types/home.ts + mock data JSON
3. MSW handler 등록
4. PanelScroll / EmptyState / ErrorState / SkeletonCard 공용
5. RightPanel (가장 단순)
6. CenterPanel (필터 + 리스트)
7. LeftPanel = CubeCarousel + 면 4개
8. Pinia store 결합 + bootstrap
9. L1 (Vitest) + L2 (Playwright mock) 작성
10. lint / type / build / 번들 회귀 확인
