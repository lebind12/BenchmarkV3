---
feature_id: fixture-detail
phase: mock
author: fe-planner
created: 2026-05-14
---

# fixture-detail — 개발 방향 (devplan)

대상: fe-dev. 컴포넌트 트리 / store / MSW handler / endpoint 후보 / 포메이션 룩업.

본 feature 는 `main-home` feature 에서 도입한 `DefaultLayout` / `AppHeader` / `PanelScroll` / `EmptyState` / `ErrorState` / `SkeletonCard` / `LeagueBadge` / `lib/league-colors.ts` 를 **재사용**한다. (main-home 머지 전이면 fe-dev 는 본 feature 작업 시 동일 컴포넌트를 stub 으로 생성 후 main-home 머지 시 통합.)

---

## 1. 라우팅

- vue-router:
  - path: `/fixtures/:externalId(\\d+)`
  - name: `fixture-detail`
  - component: `() => import('@/views/FixtureDetailView.vue')`
  - meta: `{ layout: 'default', title: '매치' }`
- 쿼리: `?tab=formation|h2h|stats|standings` (default = formation)

---

## 2. 디렉토리 / 파일

```
frontend/src/
├── views/
│   └── FixtureDetailView.vue              # 진입점
├── components/fixture/
│   ├── MatchHeader.vue                    # 25vh 헤더
│   ├── GoalHistoryInline.vue              # 골 이력 인라인
│   ├── EventsTimeline.vue                 # 좌측 25%
│   ├── EventRow.vue
│   ├── EventIcon.vue                      # event_type → 아이콘 매핑
│   ├── EventTooltip.vue
│   ├── CenterTabs.vue                     # 중앙 50% 컨테이너
│   ├── tabs/
│   │   ├── FormationTab.vue
│   │   ├── FormationPitch.vue             # 좌/우 절반 합성
│   │   ├── FormationHalf.vue              # 한 팀 포메이션 도형
│   │   ├── FormationNode.vue
│   │   ├── H2HTab.vue
│   │   ├── H2HRow.vue
│   │   ├── StatsTab.vue
│   │   ├── StatBarRow.vue
│   │   ├── StandingsTab.vue
│   │   └── StandingsRowHighlight.vue
│   ├── LineupsRight.vue                   # 우측 25% (상하 50/50)
│   ├── LineupPanel.vue                    # 한 팀 라인업
│   └── LineupRow.vue
├── stores/
│   └── fixtureDetail.ts                   # Pinia store (페이지 단위)
├── lib/
│   ├── api/fixtureDetail.ts               # fetch wrapper
│   └── formations.ts                      # 포메이션 string → 행렬 룩업
├── mocks/
│   ├── handlers/fixtureDetail.ts          # MSW
│   └── data/fixture-detail/
│       ├── match.{ns,ft,live,aet,pen,pst}.json
│       ├── events.*.json
│       ├── lineups.*.json
│       ├── h2h.*.json
│       ├── statistics.*.json
│       └── league-standings.*.json
└── types/
    └── fixtureDetail.ts
```

shadcn-vue 의존: `Tabs`, `Tooltip`, `Collapsible` (벤치 펼치기), `Button`, `Badge`, `Skeleton`, `Card`.

---

## 3. 컴포넌트 트리 (런타임)

```
DefaultLayout (from main-home)
└── AppHeader
└── FixtureDetailView   (height: calc(100vh - 56px); flex column)
    ├── MatchHeader   (25vh)
    │   ├── TeamHeaderCell (홈)
    │   ├── ScoreCell
    │   ├── TeamHeaderCell (어웨이)
    │   ├── MetaLine
    │   └── GoalHistoryInline
    └── ThreePanel    (75vh; grid 25/50/25)
        ├── EventsTimeline
        │   └── EventRow * N
        ├── CenterTabs
        │   ├── TabBar (4 items)
        │   └── <slot> = FormationTab | H2HTab | StatsTab | StandingsTab
        └── LineupsRight
            ├── LineupPanel (홈, 50%)
            │   └── LineupRow * N + Collapsible(벤치)
            └── LineupPanel (어웨이, 50%)
```

---

## 4. Pinia store — `useFixtureDetailStore(externalId)`

```ts
type Slice<T> = { status:'idle'|'loading'|'ok'|'error'|'not_found'; value:T|null; error:string|null }

interface FixtureDetailState {
  externalId: number | null
  match:     Slice<MatchDetail>            // 헤더용
  events:    Slice<TimelineEvent[]>
  lineups:   Slice<{ home: TeamLineup; away: TeamLineup }>
  h2h:       Slice<H2HFixture[]>
  statistics:Slice<{ home: TeamStat; away: TeamStat }>
  standings: Slice<{ league: LeagueRef; season: number; group_name: string | null; rows: StandingRow[]; highlighted_team_ids: [number, number] }>

  activeTab: 'formation' | 'h2h' | 'stats' | 'standings'
  benchExpanded: { home: boolean; away: boolean }
}
```

Actions:
- `bootstrap(externalId)` — match/events/lineups 병렬 fetch. URL `?tab=` 으로 activeTab 초기화
- `setTab(tab)` — activeTab 변경, 해당 탭 lazy fetch (h2h/statistics/standings)
- `toggleBench(team)` — collapsible
- `retry(slice)` — 개별 패널 재시도
- `goToFixture(id)` — H2H row 클릭 / router.push + 같은 컴포넌트 reuse → `watch(route.params.externalId)` 로 bootstrap 재실행

폴링 setInterval **사용 금지** (CLAUDE.md §6).

route param 변화 감지:
```ts
watch(() => route.params.externalId, (id) => bootstrap(Number(id)))
```

---

## 5. MSW handler 목록

`frontend/src/mocks/handlers/fixtureDetail.ts`:

```ts
import { http, HttpResponse } from 'msw'

const FIXTURE_ID_RE = /\/api\/v1\/fixtures\/(\d+)$/
const EVENTS_RE     = /\/api\/v1\/fixtures\/(\d+)\/events$/
const LINEUPS_RE    = /\/api\/v1\/fixtures\/(\d+)\/lineups$/
const H2H_RE        = /\/api\/v1\/fixtures\/(\d+)\/h2h$/
const STATS_RE      = /\/api\/v1\/fixtures\/(\d+)\/statistics$/
const STANDINGS_RE  = /\/api\/v1\/fixtures\/(\d+)\/league-standings$/

export const fixtureDetailHandlers = [
  http.get(FIXTURE_ID_RE, ({ request, params }) => pickMatch(params, request)),
  http.get(EVENTS_RE,    ({ request, params }) => pickEvents(params, request)),
  http.get(LINEUPS_RE,   ({ request, params }) => pickLineups(params, request)),
  http.get(H2H_RE,       ({ request, params }) => pickH2H(params, request)),
  http.get(STATS_RE,     ({ request, params }) => pickStats(params, request)),
  http.get(STANDINGS_RE, ({ request, params }) => pickStandings(params, request)),
]
```

mock fixture ID 규약 (테스트 분기용):
- `1000001` — FT 정상 (모든 패널 정상)
- `1000002` — NS (예정, 라인업 X, events X, 스탯 X)
- `1000003` — LIVE (1H, 일부 데이터)
- `1000004` — AET / PEN (연장 + 승부차기)
- `1000005` — 다득점 (홈 6 어웨이 4)
- `1000006` — 컵 (Carabao, standings 없음 → 토너먼트 카피)
- `1000007` — UCL 그룹 스테이지 (group_name 있음)
- `1000008` — UCL 토너먼트 (group_name null, 토너먼트 카피)
- `1000099` — 404 (DB 미존재)
- `1000098` — 500 (서버 에러 케이스)

Playwright 는 위 ID 로 진입해서 시나리오 검증.

---

## 6. TypeScript 타입

`frontend/src/types/fixtureDetail.ts`:

```ts
import type { LeagueRef, TeamRef, PlayerRef } from '@/types/home'
// LeagueRef/TeamRef/PlayerRef 는 main-home 에서 정의. 본 feature 가 import.

export type FixtureStatus =
  'NS' | '1H' | 'HT' | '2H' | 'ET' | 'BT' | 'P' | 'PEN'
  | 'FT' | 'AET' | 'PST' | 'CANC' | 'SUSP'

export interface MatchDetail {
  external_id: number
  league: LeagueRef
  round: string                       // "32라운드", "Round of 16"
  status_short: FixtureStatus
  status_long: string                 // "Match Finished" 등 (원문) — FE 는 ko 매핑
  kickoff_at: string                  // ISO8601
  venue: { name: string; city: string | null } | null
  referee: string | null
  home: TeamRef
  away: TeamRef
  goals_home: number | null
  goals_away: number | null
  penalty_home: number | null         // 승부차기 골 (PEN)
  penalty_away: number | null
  goal_events: GoalEventSummary[]     // 헤더 골 이력용 (events 와 별개 요약)
}

export interface GoalEventSummary {
  minute: number
  extra: number | null                // +n 추가시간
  scorer: PlayerRef
  team_external_id: number
  type: 'normal' | 'penalty' | 'own_goal'
}

export type TimelineEventType =
  'goal' | 'goal_penalty' | 'goal_own'
  | 'yellow_card' | 'red_card' | 'yellow_red'
  | 'substitution' | 'var'

export interface TimelineEvent {
  id: string
  minute: number
  extra: number | null
  team_external_id: number            // 홈/어웨이 컬럼 분기 키
  type: TimelineEventType
  player: PlayerRef                   // 주체 (득점자/카드받은자/IN 선수)
  assist: PlayerRef | null
  player_out: PlayerRef | null        // 교체 OUT
  detail: string | null               // tooltip 보조 (reason 등)
}

export interface LineupPlayer {
  player: PlayerRef
  number: number
  position: string                    // "GK", "CB", "CM", "ST" 등
  grid: string | null                 // "1:1" 같은 좌표 (API-Football 형식). null 이면 룩업 사용
  rating: number | null
  minutes: number | null
}

export interface TeamLineup {
  team: TeamRef
  formation: string | null            // "4-3-3"
  coach: { name: string } | null
  start_xi: LineupPlayer[]            // 11명
  bench: LineupPlayer[]
}

export interface H2HFixture {
  external_id: number
  league: Pick<LeagueRef, 'external_id'|'slug'|'short_name_ko'|'name'>
  kickoff_at: string
  home: TeamRef
  away: TeamRef
  goals_home: number
  goals_away: number
  status_short: FixtureStatus
  // 현재 match 의 홈팀 관점 결과 W/D/L 은 클라이언트 계산
}

export interface TeamStat {
  team_external_id: number
  possession: number | null                // 0~100
  shots_total: number | null
  shots_on_target: number | null
  passes_total: number | null
  passes_accuracy: number | null           // %
  corners: number | null
  fouls: number | null
  yellow: number | null
  red: number | null
  offsides: number | null
}

export interface StandingRowDetail {
  rank: number
  team: TeamRef
  played: number
  win: number
  draw: number
  loss: number
  goals_for: number
  goals_against: number
  goal_diff: number
  points: number
}
```

Integration 단계에서 zod 스키마 정의 (fe-workflow §9).

---

## 7. 새 endpoint 후보 (BE 에 신호)

| endpoint id | path / method | 비고 |
|---|---|---|
| `GET__api_v1_fixtures__id` | `GET /api/v1/fixtures/{external_id}` | 매치 헤더용. 404 시 BE 가 명확히 404 status |
| `GET__api_v1_fixtures__id__events` | `GET /api/v1/fixtures/{external_id}/events` | 타임라인 events. minute 오름차순 정렬 |
| `GET__api_v1_fixtures__id__lineups` | `GET /api/v1/fixtures/{external_id}/lineups` | 홈/어웨이 분리. start_xi 11명 + bench |
| `GET__api_v1_fixtures__id__h2h` | `GET /api/v1/fixtures/{external_id}/h2h?limit=5` | 최근 5 (기본). 시간 내림차순 |
| `GET__api_v1_fixtures__id__statistics` | `GET /api/v1/fixtures/{external_id}/statistics` | NS / live 시 NULL metric 가능 |
| `GET__api_v1_fixtures__id__league_standings` | `GET /api/v1/fixtures/{external_id}/league-standings` | 매치 리그의 현재 시즌 standings + group 필터 (UCL/UEL) + highlighted_team_ids |

⚠ `h2h_fixture` 테이블 / `fixture_event` / `fixture_lineup` / `fixture_statistics` 의 존재 여부는 BE 가 확인 필요. CLAUDE.md §4 daily-sync 책임 "fixtures / 상세" 에 포함되어 있다고 가정하나 명시 확인 필요 — devplan 으로 신호.

---

## 8. 포메이션 룩업 (lib/formations.ts)

```ts
// 포메이션 string → 라인 별 인원 행렬 (GK 부터 ST 까지, 자기 진영 → 상대 진영)
const FORMATIONS: Record<string, number[]> = {
  '4-3-3':   [1, 4, 3, 3],
  '4-4-2':   [1, 4, 4, 2],
  '4-2-3-1': [1, 4, 2, 3, 1],
  '4-3-2-1': [1, 4, 3, 2, 1],
  '3-5-2':   [1, 3, 5, 2],
  '3-4-3':   [1, 3, 4, 3],
  '5-3-2':   [1, 5, 3, 2],
  '5-4-1':   [1, 5, 4, 1],
  '4-1-4-1': [1, 4, 1, 4, 1],
  '4-5-1':   [1, 4, 5, 1],
  '3-4-2-1': [1, 3, 4, 2, 1],
  '3-4-1-2': [1, 3, 4, 1, 2],
}

export function resolveFormation(formation: string | null): number[] {
  if (!formation) return [1, 4, 4, 2]   // fallback (드물게)
  return FORMATIONS[formation] ?? [1, 4, 4, 2]
}
```

API-Football 의 `lineups[].startXI[].player.grid` (`row:col` 좌표) 가 있으면 그대로 사용 우선. 없으면 위 룩업 + 균등 분배.

좌표 → CSS:
- 좌측 절반: home. 자기 진영 = 하단. row 1 (GK) bottom: 5%; row 2 bottom: 25%; ... 균등
- 우측 절반: away. 자기 진영 = 상단. row 1 (GK) top: 5%; ...

---

## 9. 색상 / 디자인 토큰

- 헤더 배경 gradient: `linear-gradient(180deg, hsla(--league-{slug}-primary 0.08), transparent)`
- 활성 서브탭 indicator: `--league-{slug}-accent`
- 골 이력 ⚽ 아이콘: foreground
- 카드 (옐로) 🟨 / 레드 🟥: 고정 컬러 (`#FFC107` / `#E53935`)
- 빨강/녹/회 결과 배지 (H2H W/D/L): semantic tokens (success/warning/error)

---

## 10. 접근성

- 헤더 `<header>` 시맨틱
- 좌측 컬럼 2개: 부모 `role="region" aria-label="경기 이벤트 타임라인"`, 자식 `aria-label="홈 이벤트" / "어웨이 이벤트"`
- 이벤트 아이콘 = `<button>` (Tab focusable) + `aria-describedby` 로 tooltip 연결
- 포메이션 노드 = `<button>` (Tab focusable) → Enter 시 player 페이지
- 서브탭 = shadcn Tabs (자동 ARIA)
- 라인업 행 = `<button>` (Tab focusable)

---

## 11. 빌드 / 번들

- View 라우트 lazy
- 서브탭 4개 컴포넌트는 동기 import (탭 전환 즉시 반응). 단 stats/standings 의 데이터는 lazy fetch
- 이미지 lazy + width/height

---

## 12. fe-dev 작업 순서

1. types/fixtureDetail.ts (main-home types 의존)
2. mock JSON (10 fixture ID 분기) + MSW handler
3. lib/formations.ts + lib/api/fixtureDetail.ts
4. MatchHeader + GoalHistoryInline (정적 컴포넌트부터)
5. EventsTimeline + EventRow + tooltip
6. LineupsRight + LineupPanel
7. CenterTabs + 4 탭 컴포넌트
8. Pinia store 결합 + bootstrap + route param watch
9. L1 + L2 작성
10. lint / type / build / 번들 회귀
