---
feature_id: fixture-detail
source: docs/features/fixture-detail.md
ui_standards: docs/spec/ui-standards.md
league_palette: docs/spec/league-palette.md
phase: mock
author: fe-planner
created: 2026-05-14
---

# fixture-detail — 정제 요구사항 명세 (spec)

## 0. 한 줄 요약

`/fixtures/{external_id}` 매치 디테일. 56px 글로벌 헤더 아래 = (1) 매치 헤더 **25vh** + (2) 3패널 **75vh** (25/50/25). 좌 = events 타임라인 (홈/어웨이 2 컬럼, 아이콘 + hover tooltip), 중 = 서브탭 (포메이션 default / H2H / 경기 스탯 / 리그 랭킹), 우 = 홈 라인업 50% + 어웨이 라인업 50%. **DB 만** 사용 (CLAUDE.md §6 정책: 일반 페이지는 6h stale 허용, 라이브 폴링 X). 페이지 자체 스크롤 X / footer X / 패널 내부 hidden 스크롤만.

본 spec 은 메인 `docs/features/fixture-detail.md` 의 §1~§12 를 인용하며, 빈 상태 / 에러 / 데이터 shape / 인증 / 미정 항목을 구체화한다.

---

## 1. 인증 / 권한

| 항목 | 값 |
|---|---|
| 페이지 접근 | **public** (비로그인 가능) |
| 데이터 호출 | 비인증 GET |
| Role 별 분기 | 없음 (USER/STREAMER/ADMIN 모두 동일 화면) |
| 글로벌 header | main-home 과 공유 (STREAMER 만 "방송" 탭 표시) |

---

## 2. 라우팅

- URL: `/fixtures/:externalId(\\d+)` — `external_id` 는 숫자 (API-Football fixture.id)
- vue-router `params.externalId` → `Number(...)` 변환
- 페이지 미발견 (DB 에 없음) → `404` 페이지 (별 feature) 로 `router.replace`. 본 feature 는 fetch 가 404 응답 시 동일 처리

---

## 3. 전체 Layout

```
height: 100vh;
overflow: hidden;
├── AppHeader            (56px 고정, 전역)
└── main                  (height: calc(100vh - 56px); flex column)
    ├── MatchHeader       (height: 25vh)              ← 매치 헤더
    └── ThreePanel        (height: 75vh; grid 25/50/25)
        ├── EventsTimeline (25%)
        ├── CenterTabs     (50%)
        └── LineupsRight   (25%, 위/아래 50%)
```

> 메인 §11 명시: 헤더 25vh + 패널 25/50/25 비율은 FE 변경 금지.

`100vh` 가 아닌 `calc(100vh - 56px)` 안에서 25vh / 75vh 가 적용되어야 함. 즉:
- MatchHeader 실제 높이 = `25vh` 그대로 (메인 명세). 결과 패널 높이 = `calc(100vh - 56px - 25vh)` = 75vh - 56px. 시각 차이가 1366×768 등 작은 viewport 에서 발생 가능 → fe-dev 는 1366×768 에서도 매치 헤더 + 3패널 모두 fit 함을 시각 회귀로 확인.

---

## 4. 매치 헤더 (25vh)

### 4.1 표시 항목 (메인 §5.2 그대로)

```
[home logo (큰)]      3  -  1       [away logo (큰)]
홈팀 name_ko                          어웨이팀 name_ko

league.name_ko · 32라운드 · FT · Anfield · J. Pratt · 2026-05-13 19:00 KST

⚽ Salah 23'  /  ⚽ Saka 45'+2  /  ⚽ Son 67'  /  ⚽ De Bruyne 89'
```

### 4.2 status 별 분기

| status | 스코어 자리 | 골 이력 자리 |
|---|---|---|
| NS (예정) | `vs` | "kickoff 19:00 KST" 텍스트 (카운트다운 X — CLAUDE.md §6 라이브 표시 금지 일관성) |
| 1H/HT/2H/ET/BT (라이브) | **DB 마지막 sync 값** (예: `1 - 0`). 라이브 갱신 안 함 (최대 6h stale). status 배지에 "FT 표시 아님" 텍스트는 X. 단순히 `1H` 등 status_short 표시 | 골 이력 = 마지막 sync 시점까지 |
| FT/AET/PEN | 최종 스코어 (PEN 은 `5(3) - 5(2)` 같이 괄호로 승부차기) | 정규 시간 + ET + PEN 모든 골 표시 |
| PST/CANC/SUSP | 스코어 자리 = "—" + status 배지 ("연기" / "취소" / "중단") | "경기가 진행되지 않았습니다" |

### 4.3 골 이력 표시 정책 (메인 §12 결정)

- **인라인 표기**: `⚽ {scorer.name_ko} {minute}'` 를 `/` 로 구분, flex-wrap 으로 줄바꿈 허용
- 8골+ 다득점 대응: 폰트 size auto downscale (clamp(11px, 0.85vw, 14px)) + 줄바꿈 허용. **가로 스크롤 금지**
- penalty / own goal 표기:
  - `(PEN)` 접미사 = 페널티골
  - `(OG)` 접미사 = 자책골 (점수 귀속은 BE 처리; 표시 라벨만 FE)
- assist 정보는 표시 안 함 (헤더 공간 절약, 좌측 타임라인에서 hover tooltip 으로)

### 4.4 메타 라인 정책

- 미들dot `·` 로 구분
- `venue.name` / `referee` / `kickoff_at` 중 NULL 인 항목은 표기 자체 생략 (앞 뒤 dot 도 같이 제거)
- 시간: KST 변환 + `YYYY-MM-DD HH:MM` 형식

### 4.5 색상

- 헤더 배경 = `--league-{slug}-primary` (해당 매치 리그) light overlay (alpha 0.08) gradient
- 팀명 / 메타 텍스트 = `--foreground`

---

## 5. 좌측 25% — events 타임라인

### 5.1 구조

```
┌──────────────┬──────────────┐
│   홈          │   어웨이      │   ← 2 컬럼 (50/50)
├──────────────┼──────────────┤
│      ⚽ 23'   │               │
│               │   🟨 31'      │
│               │      ⚽ 45'+2 │
│   🔄 60'      │               │
│      ⚽ 67'   │               │
│   🟥 78'      │               │
│               │      ⚽ 89'   │
└──────────────┴──────────────┘
(위→아래 시간 순. 같은 분 충돌은 양 컬럼 동시 row)
```

- 각 row 는 time 기준 정렬 (1' → 90'+추가시간 → ET → PEN)
- 한 row 안에서 해당 팀 컬럼에만 아이콘 표시, 반대 컬럼은 빈 칸
- 컬럼 내부 row 는 추가시간 차등 padding 으로 시간 흐름 시각화 (선택)

### 5.2 이벤트 종류 / 아이콘

| event_type | 아이콘 | hover tooltip 내용 |
|---|---|---|
| `goal` | ⚽ | `{minute}' — {scorer.name_ko} ⚽ ({assist.name_ko} 어시)?` |
| `goal_penalty` | ⚽(P) | `{minute}' — {scorer.name_ko} 페널티골` |
| `goal_own` | ⚽(OG) | `{minute}' — {scorer.name_ko} 자책골` |
| `yellow_card` | 🟨 | `{minute}' — {player.name_ko} 경고 ({reason})?` |
| `red_card` | 🟥 | `{minute}' — {player.name_ko} 퇴장` |
| `yellow_red` | 🟨→🟥 | `{minute}' — {player.name_ko} 경고 누적 퇴장` |
| `substitution` | 🔄 | `{minute}' — IN {player_in.name_ko} / OUT {player_out.name_ko}` |
| `var` | 🎬 | `{minute}' — VAR ({result})` |

### 5.3 tooltip

- shadcn-vue `Tooltip` 컴포넌트
- hover 또는 keyboard focus 시 표시 (접근성)
- 표시 위치: 아이콘 우측 / 좌측 자동 flip (스크린 가장자리 대응)
- delay: 200ms

### 5.4 빈 / 에러 상태

| 시나리오 | UI |
|---|---|
| events 0건 (NS) | "경기 시작 전입니다" placeholder + 시계 아이콘 |
| events 0건 + status=FT (드물게 발생) | "경기 이벤트 정보가 없습니다" |
| fetch error | "이벤트를 불러오지 못했습니다" + 다시 시도 버튼 (좌측 패널 격리) |

### 5.5 스크롤

내부 hidden 스크롤 (UI 표준 §1.2). 90분+추가시간+ET+PEN 모두 한 패널에 안 들어올 가능성 — 휠/키보드 정상 동작. 상/하단 fade-out gradient.

### 5.6 데이터

- mock endpoint: `GET__api_v1_fixtures_:id_events` → `{ events: TimelineEvent[] }`
- 한 응답에 events 모두. 클라이언트가 home/away 컬럼 분리.

---

## 6. 중앙 50% — 서브탭

### 6.1 서브탭 (가로 탭, height ~40px)

| 라벨 | 기본 | 비고 |
|---|---|---|
| **포메이션** | ✅ default | mount 시 활성 |
| H2H | | 최근 5 |
| 경기 스탯 | | bar 비교 |
| 리그 랭킹 | | 매치 리그 standings |

shadcn-vue `Tabs` 사용. 활성 탭 indicator 색상 = 매치 리그 `--league-*-accent`.

URL 쿼리로 활성 탭 보존 (`?tab=h2h` 등). 새로고침 시 그 탭 복원. 기본은 쿼리 없음 = 포메이션.

### 6.2 포메이션 (default)

```
┌─────────────────┬─────────────────┐
│  홈 4-3-3       │  어웨이 4-2-3-1  │
│    GK           │      ST  ST     │
│  CB CB CB CB    │    AM AM AM     │
│   CM CM CM      │    DM   DM      │
│   ST ST ST      │  CB CB CB CB    │
│                 │      GK         │
└─────────────────┴─────────────────┘
```

- 좌측 절반 = 홈 (자기 진영 아래 = GK), 우측 절반 = 어웨이 (자기 진영 위 = GK)
- 좌표는 포메이션 string 에서 결정. 룩업 테이블 (`'4-3-3' → [[1],[4],[3],[3]]` 같은 행렬)
- 행 = 라인. 라인 안 위치 = 균등 분배
- 각 노드 = `<button>` (포커스 가능) + 등번호 (큰 글씨) + name_ko (작은 글씨, 1줄 ellipsis)
- 클릭 → `/players/{slug}`
- hover → 평점 + 분(min played) tooltip (rating 데이터 있을 때만, NULL 이면 tooltip 비활성)
- 색상: 노드 배경 = `--league-{slug}-primary` low alpha. 등번호 색 = `--league-{slug}-on-primary`

#### 빈 / 폴백
- 포메이션 string NULL (NS 면 일반적) → "라인업 미정 (kickoff 1시간 전 발표)" placeholder (메인 §5.5 동일 카피)
- 포메이션 알 수 없음 (예: API 응답에 lineup.formation NULL 인데 선수 11명만 있음) → 일반 list 폴백 (선수 11명 grid)

### 6.3 H2H

- 양 팀 직접 대결 최근 5 경기
- 시간 내림차순 (최신 위)
- 각 row: `날짜 · league.short_name_ko · 홈팀 logo 홈팀명 - score - 어웨이팀명 어웨이팀 logo · 결과 배지`
- 결과 배지 (현재 매치의 홈팀 관점): `승 W` 녹색 / `무 D` 회색 / `패 L` 적색
- row 클릭 → `/fixtures/{external_id}` (그 H2H 경기로 이동)
- 5 경기 모두 viewport 안에 표시 (스크롤 없이) — 메인 §5.4 H2H. 실제로는 약 56px × 5 = 280px ≤ 50% × 75vh @ FHD ≈ 405px 로 fit
- 빈: H2H 없음 ("두 팀 간 최근 5경기 기록이 없습니다") / 컵 처음 만남도 같은 카피

### 6.4 경기 스탯

각 row = 좌측 홈 값 / 중앙 라벨 / 우측 어웨이 값, 가로 bar 비교 (홈쪽은 좌→중앙, 어웨이쪽은 우→중앙).

표시 지표 (메인 §5.4):
- 점유율 (%)
- 슛 (총 / 유효) — 2 row
- 패스 (총 / 정확도 %) — 2 row
- 코너킥
- 파울 / 옐로 / 레드 — 3 row
- 오프사이드

상태 분기:
- NS → 전체 비활성 ("경기 시작 전 통계가 없습니다")
- 라이브 (1H/HT/2H/ET) → 표시. 일부 metric 이 NULL (예: 정확도 미계산) 이면 그 row 에 "—"
- FT/AET/PEN → 전체 표시

데이터: `GET__api_v1_fixtures_:id_statistics` → `{ home: TeamStat, away: TeamStat }` (각 TeamStat 은 metric → value map)

### 6.5 리그 랭킹

- 매치의 `league_id` 의 현재 시즌 standings
- 표 컬럼: rank · team logo · `team.name_ko` · played · W-D-L · GD · points
- 양 팀 row 강조: 행 배경 = `--league-{slug}-primary` low alpha + 좌 border 4px (홈 = 진한 / 어웨이 = 보조색)
- 클릭 → `/teams/{slug}` (해당 팀 페이지)
- UCL/UEL 매치: standings 가 `group_name` 별로 묶여 있음 → 매치 팀들의 group 만 표시 (다른 그룹 X). 토너먼트 스테이지면 빈 응답 → "토너먼트 스테이지: 그룹 순위가 없습니다" 카피 + bracket 링크 (`/standings/{league_slug}#bracket` MVP 외, link 만)
- Carabao / FA Cup: standings 자체 없음 → 같은 빈 카피 + bracket 링크

데이터: `GET__api_v1_fixtures_:id_league_standings` → `{ league: LeagueRef, season: number, group_name: string | null, rows: StandingRow[], highlighted_team_ids: [home_id, away_id] }`

### 6.6 패널 내부 스크롤

- 포메이션 / H2H 는 스크롤 거의 없음
- 경기 스탯 / 리그 랭킹은 스크롤 가능. hidden-scrollbar + fade-out

---

## 7. 우측 25% — 라인업 (홈 50% + 어웨이 50%)

### 7.1 구조

```
┌─────────────────────────┐
│   홈 라인업 (50%)        │
│   포메이션: 4-3-3        │
│   ────────────           │
│   1  GK  Alisson         │
│   66 RB  Alexander-Arnold│
│   ...                    │
│   ────────────           │
│   벤치 (펼치기 ▼)        │
├─────────────────────────┤
│   어웨이 라인업 (50%)    │
│   ...                   │
└─────────────────────────┘
```

### 7.2 한 라인업 영역

| 영역 | 내용 |
|---|---|
| 헤더 | "홈 라인업 · {formation}" (예: "홈 라인업 · 4-3-3") + 코치명 (있을 때) |
| 선발 11명 | 행: `{등번호} {position} {player.name_ko}` (영문 fallback). position = "GK/CB/CM/ST" 등 (API-Football `lineups[].startXI[].player.pos`) |
| 벤치 | 기본 접힘. "벤치 ▼" 토글. 펼침 시 같은 형식 |
| 카드 클릭 | `/players/{slug}` |
| 평점 표시 | API-Football `lineups[].startXI[].statistics.rating` 가 있으면 우측 끝에 (예: `7.4`). 없으면 X. 라이브 매치는 종종 NULL |
| 빈 (NS) | "라인업 미정 (kickoff 1시간 전 발표)" placeholder |
| 패널 스크롤 | 11 + 벤치 = 약 20명. 50% × 75vh 에 다 안 들어가면 hidden 스크롤 |

### 7.3 데이터

`GET__api_v1_fixtures_:id_lineups` → `{ home: TeamLineup, away: TeamLineup }`
TeamLineup: `{ team: TeamRef, formation: string | null, coach: { name: string } | null, start_xi: LineupPlayer[], bench: LineupPlayer[] }`
LineupPlayer: `{ player: PlayerRef, number: number, position: string, rating: number | null, minutes: number | null }`

본 endpoint 의 응답을 **포메이션 탭** (§6.2) 도 공유한다 (Pinia store 에서 캐싱).

---

## 8. 글로벌 fetch / 상태

### 8.1 페이지 진입

```
mount HomeView('fixture-detail')
  └─ Promise.all([
       GET /fixtures/:id            → MatchHeader 데이터
       GET /fixtures/:id/events     → 좌측 타임라인
       GET /fixtures/:id/lineups    → 우측 라인업 + 중앙 포메이션 (default 탭)
       GET /fixtures/:id/h2h        → 중앙 H2H 탭 (지연 lazy 가능)
       GET /fixtures/:id/statistics → 중앙 스탯 탭 (lazy 가능)
       GET /fixtures/:id/league-standings → 중앙 리그 랭킹 탭 (lazy 가능)
     ])
```

lazy 정책:
- match / events / lineups : 즉시 (3개 패널 핵심)
- h2h / statistics / league-standings : **첫 탭 활성화 시** fetch. cache 한 번 받으면 유지

### 8.2 매치 미발견

- `GET /fixtures/:id` 가 404 → `router.replace({ name: 'not-found' })` (전역 404 페이지로)
- 본 feature 는 404 페이지 자체를 만들지 않음 (별 feature). 임시로 placeholder 컴포넌트 inline 렌더 (`<NotFoundInline />`)

### 8.3 패널 격리

events fetch 실패가 lineups 에 영향 X. 각 패널 자체 에러 박스.

### 8.4 polling 없음

CLAUDE.md §6 일반 페이지 정책. 라이브 매치라도 자동 갱신 X. 사용자가 새로고침 해야 최신. "이 페이지는 6시간마다 갱신됩니다" 안내 텍스트 헤더 하단에 1회.

---

## 9. 비기능 (메인 §7 정제)

| 항목 | 값 |
|---|---|
| 데이터 신선도 | 6h (DB only) |
| 폴링 | **없음** (CLAUDE.md §6 + 메인 §11) |
| 페이지 스크롤 | **금지** |
| footer | **없음** |
| 패널 내부 스크롤 | hidden-scrollbar + fade-out gradient |
| LCP | < 1.5s |
| 번들 회귀 | < 10% |
| 뷰포트 | 1920×1080 최적 / 1366×768 최소 동작 (헤더 25vh + 75vh 패널 모두 fit 검증) |
| 접근성 | tooltip 키보드 활성, 포메이션 노드 keyboard navigation, 컬럼 aria-label "홈 이벤트" / "어웨이 이벤트" |
| 시간대 | KST 표기 |

---

## 10. 도메인 / SSOT 점검

| 항목 | 결과 |
|---|---|
| 5리그 한정 | ✅ 본 페이지는 매치가 5리그 (또는 향후 ADMIN 추가 활성 리그) 일 때만 진입. external_id 매핑 불가 시 404 |
| 2시즌 보관 | ✅ 본 매치는 current 또는 직전 시즌 데이터. 더 오래된 매치 ID 는 DB 부재 → 404 |
| 라이브 폴링 | ✅ 폴링 없음. 라이브 매치라도 6h stale 허용 (메인 §1 / §7) |
| 방송용 페이지 | ❌ 해당 안 됨 (메인 §4 "no") |
| 새 외부 데이터 의존성 | ❌ 모두 기존 도메인 (`fixture`, `fixture_event`, `fixture_lineup`, `standings`, `h2h_fixture`) |

→ **충돌 없음**, `PLAN_DRAFTING` 진행.

---

## 11. 메인 §11 권한 경계 준수

- URL `/fixtures/{external_id}` 유지 ✅
- 헤더 25vh + 패널 25/50/25 비율 유지 ✅
- 서브탭 4 항목 (포메이션/H2H/스탯/리그 랭킹) 유지 ✅
- 좌측 타임라인 = 아이콘 + hover 방식 유지 ✅
- 라이브 갱신 없음 유지 ✅

---

## 12. 빈/에러 카피 일람

| 위치 | 카피 |
|---|---|
| 헤더 NS | "kickoff {HH:MM} KST" |
| 헤더 PST/CANC | "연기됨" / "취소됨" |
| events 0 (NS) | "경기 시작 전입니다" |
| events 0 (FT) | "경기 이벤트 정보가 없습니다" |
| events fetch err | "이벤트를 불러오지 못했습니다 — 다시 시도" |
| 포메이션 NS | "라인업 미정 (kickoff 1시간 전 발표)" |
| H2H 0 | "두 팀 간 최근 5경기 기록이 없습니다" |
| 스탯 NS | "경기 시작 전 통계가 없습니다" |
| 리그 랭킹 (토너먼트) | "토너먼트 스테이지: 그룹 순위가 없습니다" |
| 라인업 NS | "라인업 미정 (kickoff 1시간 전 발표)" |
| 매치 미발견 (404) | "존재하지 않는 경기입니다 → 메인으로" (별 feature 의 404, 본 feature 는 redirect) |
| 안내 텍스트 (전역) | "이 페이지는 6시간마다 갱신됩니다" |

---

## 13. 미정 / 메모 (메인 §12 응답)

| 메인 §12 항목 | 본 spec 결정 |
|---|---|
| 포메이션 도형 좌표 | 룩업 테이블로 행렬 결정 (devplan 참조). 4-3-3 / 4-4-2 / 4-2-3-1 / 3-5-2 / 5-3-2 / 3-4-3 등 일반 포메이션 사전 정의 |
| 골 이력 다득점 | 인라인 + 줄바꿈 + 폰트 clamp. 가로 스크롤 금지 |
| 라이브 stale 6h | 의도된 정책 그대로. 메인 페이지처럼 헤더 하단 안내 1회 |
| rating 표시 | API 응답에 있으면 표시, 없으면 생략 |
| 404 처리 | 전역 404 페이지로 redirect (별 feature) |
