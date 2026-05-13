---
feature_id: main-home
source: docs/features/main-home.md
ui_standards: docs/spec/ui-standards.md
league_palette: docs/spec/league-palette.md
phase: mock
author: fe-planner
created: 2026-05-14
---

# main-home — 정제 요구사항 명세 (spec)

## 0. 한 줄 요약

`/` 홈 페이지. 단일 viewport (`100vh - 56px header`) 안에 좌(25%) / 중(50%) / 우(25%) 3패널을 fit. 페이지 자체 스크롤 X, footer X. 좌측 = 로고(30%) + 3D 큐브(70%, 4면 자동 회전 10초). 중앙 = 오늘 경기 + 리그/기간 필터. 우측 = 리그 팀 순위(50%) + 선수 스탯(50%). 모든 데이터 출처는 **DB 만** (라이브 X).

본 spec 은 메인 `docs/features/main-home.md` 의 §1~§12 를 그대로 인용하며, FE 가 결정해야 하는 흐름 / 상태 / 데이터 shape 가정 / 인증을 구체화한다.

---

## 1. 인증 / 권한

| 항목 | 값 |
|---|---|
| 페이지 접근 | **public** (비로그인 가능, JWT 불요) |
| 데이터 호출 | 모두 비인증 GET endpoint 가정 |
| 우상단 토글 | 비로그인 → "로그인" 버튼 (`/auth/login` link). 로그인 → "프로필" 메뉴 (이름 + 드롭다운, MVP 는 "로그아웃" 항목만) |
| STREAMER role | 상단 탭에 "방송" 추가 표시 (`/broadcast`). 그 외 메인 동일 |
| ADMIN role | 메인 동일. 별도 분기 X |

→ 인증 상태는 Pinia `useAuthStore` (이미 존재한다고 가정) 의 `user.role` 로 분기. mock 단계에서는 `localStorage.mockRole` 값(`public|USER|STREAMER|ADMIN`) 으로 전환 (devplan 참조).

---

## 2. 라우팅 / 페이지 구조

### 2.1 URL
- `/` (vue-router root path)
- 쿼리 파라미터: **없음** (필터는 in-memory state. 새로고침 시 기본값으로 복귀)

### 2.2 상단 탭 (전역 header)
높이 56px 고정. 본 feature 에서는 **렌더링만 책임**, 라우팅 동작 검증은 별 feature.

탭 목록 (메인 §5.1 그대로):
- 홈 `/` (active)
- 경기 `/fixtures`
- 순위 `/standings`
- 팀 `/teams`
- 선수 `/players`
- 스탯 `/stats`
- (STREAMER 만) 방송 `/broadcast`

### 2.3 메인 영역 layout
```
height: calc(100vh - 56px); overflow: hidden;
display: grid; grid-template-columns: 25% 50% 25%;
```

3패널 모두 `overflow: hidden` 컨테이너. 내부 콘텐츠가 넘치면 자식 element 에서 hidden-scrollbar (`scrollbar-width: none`) 처리.

---

## 3. 좌측 패널 (25%) — 로고 + 3D 큐브

### 3.1 분할
- 상단 30% : 사이트 로고 (브랜드 영역, 정적 SVG)
- 하단 70% : 3D 큐브 + 하단 dot 인디케이터

### 3.2 큐브 동작
| 항목 | 값 |
|---|---|
| 회전 축 | Y 축 (rotateY) |
| 면 수 | 4 (News / Hot 선수 / Transfer / Injury) |
| 1면 표시 시간 | **10초** (메인 §11: 변경 불가) |
| 자동 회전 | 활성 (페이지 mount 시 시작) |
| 정지 조건 | 큐브 영역 `mouseenter` + 내부 element `focusin` 모두 정지. `mouseleave` + `focusout` 시 재개 |
| dot 인디케이터 | 4개. 현재 면 강조. 클릭 시 그 면으로 즉시 이동 (회전 애니메이션 + 자동 회전 timer reset) |
| dot 라벨 | "뉴스 / 핫 / 이적 / 부상" (한글 표기, fe-planner 결정) |
| 접근성 | `role="region" aria-roledescription="carousel" aria-label="홈 큐브"` + 각 면 `aria-roledescription="slide"` + `aria-live="polite"` (자동 전환 알림) |
| 키보드 | dot 영역 `tab` 진입 → ←/→ 화살표로 dot 이동, Enter/Space 로 선택 |
| 큐브 CSS | `perspective: 1000px` on 컨테이너. 면 = `transform-style: preserve-3d`. 회전 트랜지션 `transform 0.8s ease-in-out` |

### 3.3 4면 콘텐츠 (각 정확히 5건)

| 면 | 라벨 | 한 카드 표시 | 클릭 시 | 빈 상태 |
|---|---|---|---|---|
| 1 | 뉴스 (News) | 썸네일(없으면 회색 placeholder) + `title_ko` (2줄 ellipsis) + 출처 도메인 + 게시 시각 (상대시간 "3시간 전") | 새 탭으로 원문 URL 외부 link (`target="_blank" rel="noopener noreferrer"`) | "오늘 EPL 관련 뉴스가 없습니다" placeholder 1장 |
| 2 | 핫 선수 (Hot) | 선수 사진 + `name_ko` + 팀 배지 + `골 + 어시스트` 합산점 + 리그 배지 | `/players/{slug}` | "시즌 휴식 중입니다" placeholder |
| 3 | 이적 (Transfer) | 선수 사진 + `name_ko` + `from team → to team` + 날짜 (YYYY-MM-DD) | `/stats` (이적 섹션 anchor) | "최근 이적 정보가 없습니다" placeholder |
| 4 | 부상 (Injury) | 선수 사진 + `name_ko` + 팀 배지 + 부상 종류 + 복귀 예상 (있을 때) | `/stats` (부상 섹션 anchor) | "현재 보고된 부상자가 없습니다" placeholder |

- 모든 카드: `cursor: pointer`, hover 시 보더 강조, focus outline.
- 5건이 안 나오면 placeholder 로 부족분을 채우지 않고 **있는 만큼만** 표시 + 마지막에 "이 정보는 6시간마다 갱신됩니다" 텍스트.
- 카드 하나 = 64px ~ 80px 높이 + gap 8px. 5건 모두 한 면(큐브 면 = 70% × 25% viewport ≈ 420×432 @ FHD) 안에 fit. 넘치면 그 면 내부 hidden 스크롤 허용 (휠/키보드 가능, 시각 스크롤바 없음).

### 3.4 데이터 fetch

| 면 | mock endpoint id | response shape (TS) |
|---|---|---|
| 뉴스 | `GET__api_v1_home_news` | `{ items: NewsItem[5] }` |
| 핫 | `GET__api_v1_home_hot_players` | `{ items: HotPlayer[5] }` |
| 이적 | `GET__api_v1_home_transfers` | `{ items: Transfer[5] }` |
| 부상 | `GET__api_v1_home_injuries` | `{ items: Injury[5] }` |

shape 상세는 devplan §6 참조.

---

## 4. 중앙 패널 (50%) — 오늘 경기 + 필터

### 4.1 상단 필터 영역 (고정 높이 ~96px)

```
[전체] [EPL] [UCL] [UEL] [카라바오] [FA]     ← 리그 탭 (가로 스크롤 X, 1행)
[월] [주] [일]                                ← 기간 토글 (3개)
```

| 항목 | 동작 |
|---|---|
| 리그 필터 | shadcn-vue Tabs. 기본 = "전체". 6개 (전체 + 5리그). 활성 탭 배경에 해당 리그 `--league-*-primary` 적용 (전체 = muted). 변경 시 fixture 리스트 재로드 |
| 기간 필터 | shadcn-vue ToggleGroup (single). 기본 = "일" (오늘). "월" = 이번 달, "주" = 이번 주 (월~일), "일" = 오늘 (KST 기준 0시~다음 0시). 변경 시 재로드 |
| 표시 범위 | 클라이언트 timezone = KST (Asia/Seoul) 고정 |

### 4.2 fixture 리스트

위 필터 영역 아래 = 패널 내부 hidden 스크롤 영역.

각 카드 (~72px 높이):
```
[리그 배지] [홈 logo] 홈팀 이름 ko      vs / 19:00 / 3-1      어웨이팀 이름 ko [어웨이 logo]   [status]
```

| 컬럼 | 표시 |
|---|---|
| 리그 배지 | `league.short_name_ko` (영문 fallback) + 리그 색상 배경 |
| 홈/어웨이 | logo + `team.name_ko` (영문 fallback, max 2줄 ellipsis) |
| 중앙 | NS → `kickoff_at` HH:MM (KST); LIVE 메인 표시 안 함 (정책상 NS 처럼 보일 수 있음, 6h stale 허용); FT/AET/PEN → `{goals_home} - {goals_away}` |
| status badge | NS / FT / AET / PEN / PST / CANC 텍스트 배지 |
| 클릭 | `/fixtures/{external_id}` 이동 |

(CLAUDE.md §6 정책: 일반 페이지는 DB만 사용, polling 없음. 라이브 표시 X. 메인 §7 "라이브 데이터 메인 표시 X" 와 일치.)

### 4.3 상태

| 상태 | UI |
|---|---|
| 로딩 (필터 변경 직후) | 스켈레톤 카드 8개 + 필터 영역은 즉시 반영 |
| 빈 (해당 필터 조합 경기 0건) | 가운데 정렬 "선택한 조건에 경기가 없습니다" + 아이콘 + "기간 변경" 버튼 (= 기본값으로 reset) |
| 에러 (fetch 실패) | "데이터를 불러오지 못했습니다. [다시 시도]" 버튼. 좌/우 패널은 영향 없음 |
| 정상 | 카드 리스트. 스크롤 가능 시 하단 fade-out gradient (UI 표준 §1.3) |

### 4.4 데이터 fetch

| mock endpoint id | 응답 |
|---|---|
| `GET__api_v1_home_fixtures` | `{ items: FixtureSummary[], filters_applied: { league_id?: number, period: 'day'|'week'|'month' } }` |

쿼리: `?league_id=<id>&period=<day|week|month>` (league_id 생략 = 전체).

---

## 5. 우측 패널 (25%) — 순위 (50%) + 스탯 (50%)

### 5.1 상단 50% — 리그별 팀 순위

```
[EPL ▼]                       ← 리그 드롭다운 (fe-planner 결정: 드롭다운 채택)
1.  Liverpool       72  22-6-4
2.  Arsenal         68  20-8-4
...
```

| 항목 | 값 |
|---|---|
| 리그 선택 | shadcn-vue Select (드롭다운). 기본 = EPL. 옵션 = 5리그 (current season standings 존재하는 리그만, 컵 대회 carabao/FA 는 standings 없을 수 있어 그 때만 비활성) |
| 행 | rank · `team.short_name_ko` (없으면 영문) · points · `W-D-L` |
| 클릭 | row 클릭 → `/teams/{team_slug}` |
| 스크롤 | 내부 hidden 스크롤. 헤더 행은 sticky |
| 로딩 | 스켈레톤 8행 |
| 빈/에러 | "{리그명} 순위를 불러오지 못했습니다" / "현재 진행 중인 시즌 없음" + 다른 리그 선택 유도 |

데이터: `GET__api_v1_home_standings?league_id={id}` → `{ league: LeagueRef, season: number, rows: StandingRow[] }`

### 5.2 하단 50% — 리그별 선수 스탯

```
[Goal ▼] [EPL ▼]            ← 지표 + 리그 (둘 다 드롭다운)
1.  Haaland     22
2.  Salah       18
...
```

| 항목 | 값 |
|---|---|
| 지표 선택 | shadcn-vue Select. 옵션 = `goals` (default) / `assists` / `yellow_cards` / `red_cards`. "지표명" 한글 표기 |
| 리그 선택 | shadcn-vue Select. 기본 = EPL |
| 행 | rank · `player.name_ko` (없으면 영문) · 팀 배지 (micro) · 수치 |
| 클릭 | row → `/players/{player_slug}` |
| 스크롤 | 내부 hidden 스크롤 (top 30 정도) |
| 빈/에러 | 동일 패턴 |

데이터: `GET__api_v1_home_top_players?league_id={id}&metric={goals|assists|yellow_cards|red_cards}` → `{ league: LeagueRef, season: number, metric: string, rows: TopPlayerRow[] }`

---

## 6. 글로벌 상태 / 에러 / 로딩

### 6.1 페이지 진입 (cold load)

1. 큐브 4면 fetch 병렬 시작 → 면별 로딩 스켈레톤
2. 중앙 fixtures fetch → 스켈레톤 8장
3. 우측 standings (EPL) + top_players (goals/EPL) 병렬 → 스켈레톤
4. 각 fetch 독립적으로 도착하면 그 영역만 채움
5. 전부 도착 후에도 백그라운드 polling 없음 (메인 §7)

### 6.2 패널 격리

한 fetch 실패가 다른 패널 영향 X. 각 패널은 자체 에러 박스 + "다시 시도" 버튼.

### 6.3 다크/라이트 토글

우상단 토글. localStorage `theme` 저장. system prefers-color-scheme 초기 반영.

---

## 7. 비기능 (메인 §7 정제)

| 항목 | 값 |
|---|---|
| 데이터 신선도 | 일반 = 6h (DB only), 뉴스 = 1h (news-fetcher). 화면에는 "6시간마다 갱신" 안내 텍스트 1회 |
| 폴링 | 없음 (메인 §7 + CLAUDE.md §6 정책 준수) |
| LCP | < 1.5s @ 1920×1080 |
| 번들 회귀 | < 10% vs main |
| 뷰포트 | 최적 1920×1080 / fit 1440×900 / 최소 1366×768 |
| 모바일 | MVP 외 (UI 표준 §2.1) |
| 페이지 스크롤 | **금지** (`overflow: hidden` on `body` / `#app`) |
| 패널 내부 스크롤 | hidden-scrollbar (UI 표준 §1.2 CSS 그대로) + fade-out gradient 단서 |
| 접근성 | 큐브 aria-live polite, 모든 클릭 가능 element focusable + outline, 색 대비 WCAG AA |
| 시간대 | 모든 시각 KST 표기 (예: "19:00 KST"). 상대 시간 ("3시간 전") 은 i18n 라이브러리 미사용, 자체 util |

---

## 8. 도메인 / SSOT 충돌 점검

| 항목 | 결과 |
|---|---|
| 5리그 (EPL/UCL/UEL/Carabao/FA) | ✅ 메인 §5.3 / §5.4 모두 5리그만. CLAUDE.md §2 와 일치 |
| 2시즌 | ✅ 본 페이지는 current season 한정. 직전 시즌 데이터 노출 X |
| Role 체계 | ✅ public/USER/STREAMER/ADMIN. 메인 §2 와 일치 |
| 방송용 페이지 | ✅ 본 페이지는 방송용 아님 (메인 §4 "no"). `/broadcast` 는 STREAMER 만 상단 탭 노출 |
| 라이브 폴링 | ✅ 메인 페이지 polling 없음. CLAUDE.md §6 정책 일치 |
| 새 외부 데이터 의존성 | ❌ 추가 없음 (뉴스/이적/부상은 모두 DB 기반) |
| `news_article` 사용 | ⚠ CLAUDE.md §4 워커 표에 `news-fetcher` 등재. 본 페이지 뉴스 면이 이를 소비함. devplan 의 endpoint 후보가 BE 에 신호 |

→ **충돌 없음**, `PLAN_DRAFTING` 진행.

---

## 9. 메인 §11 권한 경계 준수 확인

- URL `/` 유지 ✅
- 상단 탭 항목 (홈/경기/순위/팀/선수/스탯/방송) 유지 ✅
- 방송용 여부 (no) 유지 ✅
- 새 외부 데이터 의존성 추가 없음 ✅
- 큐브 4면 (News/Hot/Transfer/Injury) 유지 ✅
- 우측 패널 콘텐츠 (팀 순위 + 선수 스탯) 유지 ✅
- 페이지 자체 스크롤 금지 유지 ✅
- footer 추가 없음 ✅
- 자동 회전 10초 유지 ✅

---

## 10. 빈 상태 / 휴식기 정책 (메인 §12 결정 위임 분)

| 시나리오 | 동작 |
|---|---|
| 시즌 휴식기 (오늘/이번주 경기 0) | 중앙 = 빈 상태 카피 + "다음 경기일정 보기" 버튼 → `/fixtures` (기본 month) |
| 뉴스 < 5건 | 큐브 뉴스 면은 있는 만큼 표시. 부족분 placeholder 채우지 않음 |
| 컵 대회 standings 없음 (해당 리그 드롭다운 선택 시) | 빈 상태 카피 "이 대회는 토너먼트 형식이라 표 순위가 없습니다" |
| 부상/이적 0건 | 위 §3.3 빈 상태 카피 |

---

## 11. 한글 표기 정책

- 모든 entity 명: `name_ko` 우선, NULL 이면 영문 `name` fallback (CLAUDE.md §5)
- 리그 short_name 한글 라벨 (FE 결정):
  - EPL = "EPL" / UCL = "UCL" / UEL = "UEL" / 카라바오 = "카라바오" / FA = "FA"
- 큐브 dot 라벨: "뉴스 / 핫 / 이적 / 부상" (메인 §12 결정 위임)

---

## 12. 후속 / 미결

- 인증 상태별 메인 분기 (USER 만 노출되는 컴포넌트 등) — MVP 외 (메인 §12)
- WC 2026 league 등장 시 메인 노출 정책 — 별 feature
- 큐브 회전 transition easing 값 미세조정 — fe-dev 시각 확인 후 결정

## 13. 적용 — League 동적 테마 (ui-standards §3.2)

ui-standards §3.2 의 "메인 페이지 경기 카드 — 카드 좌측 보더 또는 배지 = 각 경기의 league 색" 규칙을 본 feature 도 따른다:

- 중앙 fixture 카드: 각 `FixtureCard` 의 root 에 `:data-league="fx.league.slug"` binding → `border-left: 4px solid var(--theme-primary)` (fixture-detail feature 가 도입하는 `themes.css` 재사용)
- 리그 필터 활성 탭: 활성 리그의 `var(--theme-primary)` 배경 (활성 탭 영역 자체에 `data-league` binding)
- 우측 standings/top players 블록: 선택 리그 슬러그를 블록 root 에 binding → 헤더 / select chip 색상 swap

이 모든 element 는 `--theme-*` 변수만 참조 (직접 `--league-*` 참조 금지). themes.css 미존재 시 (fixture-detail 미머지 상태) 는 main-home 작업자가 stub 생성 후 fixture-detail 머지 시 통합.
