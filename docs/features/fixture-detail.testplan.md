---
feature_id: fixture-detail
phase: mock
author: fe-planner
created: 2026-05-14
---

# fixture-detail — Playwright 테스트 플랜 (testplan)

레이어: `docs/spec/fe-workflow.md` §8. L1 Vitest / L2 Playwright + MSW / L3 Playwright integration (Vercel preview + prod BE + zod) / L4 prod smoke.

mock 머지 게이트 = L1 + L2.

테스트 분기용 fixture ID (devplan §5):
- 1000001 FT 정상 · 1000002 NS · 1000003 LIVE · 1000004 AET/PEN · 1000005 다득점
- 1000006 Carabao (standings 없음) · 1000007 UCL 그룹 · 1000008 UCL 토너먼트
- 1000099 404 · 1000098 500

---

## 1. 시나리오 매트릭스

| # | 시나리오 | 진입 | 검증 포인트 | L1 | L2 | L3 |
|---|---|---|---|---|---|---|
| F01 | FT 매치 cold load (1000001) | `/fixtures/1000001` | 헤더 25vh / 3패널 75vh / grid 25/50/25 / 모든 패널 데이터 표시 | | ✅ | ✅ |
| F02 | 페이지 자체 스크롤 금지 | 1000001 | body overflow hidden / footer X | | ✅ | |
| F03 | 1366×768 최소 viewport fit | viewport set | 헤더 + 3패널 모두 한 화면, 패널 내부 스크롤만 | | ✅ | |
| F04 | NS 매치 (1000002) | `/fixtures/1000002` | 스코어 `vs` / "kickoff 19:00 KST" / events 패널 "경기 시작 전" / 라인업 "라인업 미정" | | ✅ | |
| F05 | LIVE 매치 (1000003) — stale 표시 정책 | `/fixtures/1000003` | DB 마지막 값 그대로. polling fetch 0회 (네트워크 가로채기로 검증) | | ✅ | |
| F06 | AET / PEN (1000004) | 진입 | 스코어 `5(3) - 5(2)` 형식 / 골 이력 ET·PEN 포함 | | ✅ | |
| F07 | 다득점 8골+ (1000005) | 진입 | 골 이력 줄바꿈, 가로 스크롤 X (`scrollWidth === clientWidth`) | | ✅ | |
| F08 | PST/CANC 상태 | 1000010 (추가) | "연기됨" 배지 / "경기가 진행되지 않았습니다" | | ✅ | |
| F09 | 매치 미발견 404 → redirect | `/fixtures/1000099` | URL `/not-found` or 404 컴포넌트 표시 | | ✅ | |
| F10 | 매치 500 에러 | `/fixtures/1000098` | 글로벌 에러 패널 + "다시 시도" (헤더 영역) / 좌/우/중앙 의존 X | | ✅ | |
| F11 | 좌측 events — 홈/어웨이 컬럼 분리 | 1000001 | event[team=home] 은 좌 컬럼 / [team=away] 는 우 컬럼 | ✅ | ✅ | |
| F12 | 좌측 events — 시간 순 정렬 | 1000001 | DOM 순서 = minute 오름차순 (extra 포함) | ✅ | | |
| F13 | event hover → tooltip | 1000001 | hover 200ms 후 tooltip visible, 내용 정확 | | ✅ | |
| F14 | event keyboard focus → tooltip | 1000001 | Tab focus 시 tooltip visible (접근성) | | ✅ | |
| F15 | event 아이콘 매핑 | 1000001 | goal=⚽ / yellow=🟨 / red=🟥 / sub=🔄 등 | ✅ | | |
| F16 | events 빈 (NS) | 1000002 | "경기 시작 전입니다" | | ✅ | |
| F17 | events fetch err | scenario=event-error | 좌측 패널만 에러 박스 / 우 / 중 정상 | | ✅ | |
| F18 | 중앙 default = 포메이션 탭 | 1000001 | activeTab=formation, URL 쿼리 없음 | | ✅ | |
| F19 | 서브탭 변경 → URL 쿼리 반영 | click H2H | URL `?tab=h2h` | | ✅ | |
| F20 | URL `?tab=stats` 새로고침 | direct goto | activeTab=stats 로 복원 | | ✅ | |
| F21 | 포메이션 좌/우 분할 렌더 | 1000001 | 홈 절반 4-3-3 노드 11개 / 어웨이 절반 노드 11개 | ✅ | ✅ | |
| F22 | 포메이션 노드 클릭 → 선수 페이지 | 노드 click | URL `/players/{slug}` | | ✅ | |
| F23 | 포메이션 NS (lineup 없음) | 1000002 | "라인업 미정 (kickoff 1시간 전 발표)" | | ✅ | |
| F24 | 포메이션 NULL → list fallback | mock formation=null | 11명 grid 표시 | ✅ | | |
| F25 | H2H 5경기 표시 + 결과 배지 | tab=h2h, 1000001 | row 5개, W/D/L 배지 (홈 관점) | | ✅ | |
| F26 | H2H row 클릭 → 그 매치로 이동 | row click | URL `/fixtures/{other_id}`, bootstrap 재실행 | | ✅ | |
| F27 | H2H 0건 | scenario=no-h2h | "두 팀 간 최근 5경기 기록 없습니다" | | ✅ | |
| F28 | 경기 스탯 — 모든 metric 표시 | tab=stats, 1000001 | 점유율 슛 패스 코너 파울 옐로 레드 오프사이드 row 존재 | ✅ | ✅ | |
| F29 | 스탯 bar 비율 | 1000001 (홈 60% 어웨이 40%) | bar width style 검증 | ✅ | | |
| F30 | 스탯 NS | 1000002 | "경기 시작 전 통계가 없습니다" | | ✅ | |
| F31 | 스탯 live 시 NULL metric | 1000003 | 해당 row "—" | | ✅ | |
| F32 | 리그 랭킹 — 양 팀 row 강조 | tab=standings, 1000001 | 홈/어웨이 row 배경 highlight + border | | ✅ | |
| F33 | 리그 랭킹 row 클릭 → 팀 페이지 | row click | URL `/teams/{slug}` | | ✅ | |
| F34 | UCL 그룹 — group 만 표시 | 1000007 | 같은 group 만 row, 다른 group 없음 | | ✅ | |
| F35 | UCL 토너먼트 — 빈 카피 | 1000008 | "토너먼트 스테이지: 그룹 순위가 없습니다" | | ✅ | |
| F36 | Carabao — standings 없음 카피 | 1000006 | 동일 토너먼트 카피 | | ✅ | |
| F37 | 우측 라인업 — 11명 + 벤치 접힘 | 1000001 | start_xi 11 row visible, bench `aria-expanded=false` | ✅ | ✅ | |
| F38 | 벤치 펼치기 | 토글 click | `aria-expanded=true`, 벤치 row visible | | ✅ | |
| F39 | 라인업 행 클릭 → 선수 페이지 | row click | URL `/players/{slug}` | | ✅ | |
| F40 | 라인업 rating 표시 (있을 때) | 1000001 | row 우측에 `7.4` 형식 | ✅ | | |
| F41 | 라인업 rating NULL | 1000003 (라이브) | rating 영역 없음 | ✅ | | |
| F42 | 라인업 NS | 1000002 | placeholder "라인업 미정" | | ✅ | |
| F43 | 패널 내부 hidden 스크롤바 | 모든 패널 | computed `scrollbar-width: none` | ✅ | | |
| F44 | 패널 내부 스크롤 휠 동작 | events 패널 wheel | scrollTop 증가 | | ✅ | |
| F45 | fade-out gradient (스크롤 가능 시) | events 긴 응답 | overlay element 존재 | ✅ | | |
| F46 | polling 없음 | 1000003 LIVE, 30초 | 네트워크 fetch 횟수 = 초기 1세트 | | ✅ | |
| F47 | "6시간 갱신" 안내 노출 | 진입 | 텍스트 표시 (1회) | ✅ | | |
| F48 | 헤더 메타 NULL 항목 생략 | mock referee=null | `referee` 텍스트 미렌더, dot 누락 X | ✅ | | |
| F49 | KST 시간 표기 | kickoff 표시 | `YYYY-MM-DD HH:MM` 형식 | ✅ | | |
| F50 | 한글 fallback (name_ko=null) | mock | 영문 fallback | ✅ | | |
| F51 | 매치 리그 색상 적용 | 1000001 (EPL) | 헤더 배경 EPL primary low-alpha / 활성 탭 indicator EPL accent | | ✅ | |
| F52 | 접근성 — events 컬럼 aria-label | DOM | "홈 이벤트" / "어웨이 이벤트" | ✅ | | |
| F53 | 접근성 — 키보드 만으로 모든 탭/노드 진입 | tab cycle | 모든 클릭 element 도달 | | ✅ | |
| F54 | 응답 shape zod 검증 (모든 6 endpoint) | integration | parse 성공 | | | ✅ |
| F55 | L3 prod BE 호출 — 데이터 변경 0회 | integration | POST/PUT/DELETE count = 0 | | | ✅ |
| F56 | LCP < 1.5s | trace | margin 2.0s | | ✅ | |
| F57 | 페이지 진입 lazy fetch — h2h/stats/standings 는 탭 활성화 전 fetch X | 1000001 | network log: 초기에 h2h/stats/standings 미호출 | | ✅ | |
| F58 | **league 동적 테마 — root data-league** | EPL 매치 1000001 | `[data-testid="fixture-detail-root"]` 의 `data-league=="premier-league"` | ✅ | ✅ | |
| F59 | **league 동적 테마 — 헤더 색상 적용** | 1000001 (EPL) | MatchHeader computed background = EPL primary 톤 (`var(--theme-primary)` resolve) | | ✅ | |
| F60 | **league 동적 테마 — 서브탭 indicator** | 1000001 (EPL) → 1000007 (UCL) | 활성 탭 indicator 색상 EPL accent → UCL accent 로 swap | | ✅ | |
| F61 | **league 동적 테마 — navigate 시 swap** | 1000001 → H2H row click → 1000007 | route 변화 후 root `data-league` 갱신, 헤더 색상 변화 (screenshot 회귀) | | ✅ | |
| F62 | **league 동적 테마 — fallback (loading 중)** | 진입 직후 match.loading | `data-league` 속성 미존재, 헤더 neutral 색상 | ✅ | | |
| F63 | **league 동적 테마 — WCAG AA 대비** | 5리그 매치 각 1개 | `--theme-on-primary` text on `--theme-primary` bg 콘트라스트 ≥ 4.5:1 (axe 또는 수동 측정) | | ✅ | |
| F64 | **league 동적 테마 — 다크/라이트 모드 호환** | 1000001 EPL + 토글 | 두 모드 모두 헤더 가독 (스크린샷 baseline 2종) | | ✅ | |
| F65 | **CSS lint — `--league-*` 직접 참조 금지** | 본 feature 컴포넌트 스타일 grep | `var(--league-` 매치 0건 (theme 변수만 사용) | ✅ | | |

총 65 시나리오. L1 = 22, L2 = 40, L3 = 3.

---

## 2. L1 — Vitest 파일 배치

| 파일 | 시나리오 |
|---|---|
| `tests/unit/components/fixture/EventsTimeline.spec.ts` | F11 F12 F15 F52 |
| `tests/unit/components/fixture/GoalHistoryInline.spec.ts` | F07 (자체 단위), F48 |
| `tests/unit/components/fixture/FormationHalf.spec.ts` | F21 F24 |
| `tests/unit/components/fixture/StatBarRow.spec.ts` | F28 F29 |
| `tests/unit/components/fixture/LineupRow.spec.ts` | F37 F40 F41 |
| `tests/unit/components/common/PanelScroll.spec.ts` | F43 F45 |
| `tests/unit/components/fixture/MatchHeader.spec.ts` | F47 F48 F49 F50 |
| `tests/unit/lib/formations.spec.ts` | resolveFormation 룩업 |
| `tests/unit/stores/fixtureDetail.spec.ts` | bootstrap / setTab / lazy fetch / route watch |
| `tests/unit/views/FixtureDetailView.spec.ts` | F58 F62 (root data-league binding) |
| `tests/unit/styles/themes.spec.ts` (lint/grep style) | F65 (`--league-*` 직접 참조 0건) |

L1 게이트: vitest exit 0.

---

## 3. L2 — Playwright (mock mode)

파일: `frontend/e2e/fixture-detail.spec.ts`

```ts
test.describe('fixture-detail (mock)', () => {
  test('F01 FT 정상 cold load', async ({ page }) => {
    await page.goto('/fixtures/1000001')
    await expect(page.locator('[data-testid="match-header"]')).toBeVisible()
    // grid 검증 ...
  })
  test('F04 NS 매치', async ({ page }) => { await page.goto('/fixtures/1000002'); ... })
  test('F05 LIVE — polling 없음', async ({ page }) => {
    const reqs: string[] = []
    page.on('request', r => reqs.push(r.url()))
    await page.goto('/fixtures/1000003')
    await page.waitForTimeout(30_000)
    expect(reqs.filter(u => u.includes('/api/v1/fixtures/1000003'))).toHaveLength(/* 초기 세트만 */)
  })
  // ...
})
```

mock 시나리오 ID + scenario 쿼리 조합:
- `/fixtures/1000001?scenario=normal` (default)
- `/fixtures/1000001?scenario=event-error` (F17)
- `/fixtures/1000001?scenario=no-h2h` (F27)

L2 게이트: 모든 ✅ L2 통과 + screenshot 회귀 (헤더 / 포메이션 / 스탯 bar) + console error 0.

---

## 4. L3 — Playwright integration

`frontend/e2e-integration/fixture-detail.spec.ts`:
- Vercel preview deploy URL
- 실 prod BE
- 실 fixture id (최근 FT 매치 1개 선택; 테스트 setup 이 `GET /api/v1/home/fixtures?period=week` 에서 첫 FT 매치 ID 추출)
- 모든 6 endpoint 응답을 zod 로 parse
- POST/PUT/DELETE 호출 0회 (네트워크 가로채기로 assert)

| 시나리오 | 검증 |
|---|---|
| F01 (integration 버전) | 3패널 fit, 헤더 데이터 표시 |
| F54 | 6 endpoint zod parse 성공 |
| F55 | write request 0회 |

L3 게이트: exit 0 + zod fail 0 + write 0.

---

## 5. L4 — Prod smoke

`frontend/e2e-smoke/fixture-detail.spec.ts`:
- 최근 FT 매치 1개 진입 → 200 응답
- `[data-testid="match-header"]` visible
- console error 0

---

## 6. mock 시나리오 분기 정리

| URL | 의미 |
|---|---|
| `/fixtures/1000001` | FT 정상 (5리그 EPL 가정) |
| `/fixtures/1000001?scenario=null-ko` | name_ko / formation 일부 NULL |
| `/fixtures/1000001?scenario=event-error` | events 5xx |
| `/fixtures/1000001?scenario=no-h2h` | H2H 0건 |
| `/fixtures/1000002` | NS |
| `/fixtures/1000003` | 1H LIVE |
| `/fixtures/1000004` | AET + PEN |
| `/fixtures/1000005` | 다득점 (6-4) |
| `/fixtures/1000006` | Carabao 컵 (standings X) |
| `/fixtures/1000007` | UCL 그룹 |
| `/fixtures/1000008` | UCL 토너먼트 |
| `/fixtures/1000099` | 404 |
| `/fixtures/1000098` | 500 |

---

## 7. 통과 기준 (요약)

| 게이트 | 조건 |
|---|---|
| Mock 머지 | L1 exit 0 + L2 exit 0 + lint/type/build pass + 번들 회귀 < 10% + reviewer APPROVE |
| Integration 머지 | 위 + L3 exit 0 + zod schema pass + 데이터 변경 0회 + reviewer APPROVE |
| Prod | L4 통과 |

---

## 8. 메모

- F05 / F46 polling 검증은 fake clock 없이 30초 실측 — flaky 가능. CI 안정성 보고 fake timer 도입 검토
- 포메이션 시각 회귀 (F21) 는 4-3-3 / 4-2-3-1 / 5-3-2 baseline 3종
- LCP F56 은 trace 기준, CI margin 2.0s
- screenshot baseline: 다크/라이트 모두 (main-home 과 동일 정책)
