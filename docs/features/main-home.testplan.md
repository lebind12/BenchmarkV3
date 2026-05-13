---
feature_id: main-home
phase: mock
author: fe-planner
created: 2026-05-14
---

# main-home — Playwright 테스트 플랜 (testplan)

레이어 정의: `docs/spec/fe-workflow.md` §8 그대로.

- **L1** Vitest (unit / component) — 인메모리 mock
- **L2** Playwright + MSW — `VITE_USE_MOCK=true`, 본 feature 의 mock handler 사용
- **L3** Playwright integration — Vercel preview deploy + prod BE. 응답 zod 검증
- **L4** Prod smoke — 1회 핵심 경로

mock 라이프사이클의 머지 게이트 = **L1 + L2 통과**. L3 은 integration 라이프사이클에서 추가.

---

## 1. 시나리오 매트릭스

| # | 시나리오 | 입력 / 상태 | 검증 포인트 | L1 | L2 | L3 |
|---|---|---|---|---|---|---|
| S01 | 페이지 cold load — 모든 패널 정상 데이터 | mock 정상 | grid 25/50/25 / body overflow hidden / 4 패널 모두 데이터 표시 | | ✅ | ✅ |
| S02 | 페이지 자체 스크롤 금지 | viewport 1920×1080 | `body.scrollHeight === window.innerHeight` / footer X | | ✅ | |
| S03 | 큐브 자동 회전 (10초) | wait 10.5s | activeFace 0→1 전환 / dot 강조 이동 | | ✅ | |
| S04 | 큐브 hover 시 정지 | hover on cube | 11초 대기해도 activeFace 변화 X | | ✅ | |
| S05 | 큐브 focus 시 정지 | dot 에 tab focus | 11초 대기해도 변화 X | | ✅ | |
| S06 | 큐브 dot 클릭 이동 | dot[2] click | activeFace == 2 / face element aria-hidden 갱신 | ✅ | ✅ | |
| S07 | 큐브 키보드 (← →) 이동 | dot focus + ArrowRight | activeFace +1 | ✅ | | |
| S08 | 뉴스 카드 클릭 → 외부 URL 새 탭 | 뉴스 카드[0] click | 새 탭 열림 (target=_blank rel=noopener) | | ✅ | |
| S09 | 핫 선수 카드 클릭 → `/players/{slug}` | hot[0] click | URL 이동 | | ✅ | |
| S10 | 이적/부상 카드 → `/stats` (해당 anchor) | click | URL = /stats#transfer or /stats#injury | | ✅ | |
| S11 | 중앙 리그 필터 변경 (EPL) | tab[EPL] click | fetch 호출 query `league_id=39` / 카드 표시 EPL 만 | ✅ | ✅ | ✅ |
| S12 | 중앙 기간 필터 (월/주/일) | toggle 주 | fetch query `period=week` / 결과 행수 변화 | | ✅ | |
| S13 | 중앙 경기 카드 클릭 → 상세 | card click | URL = /fixtures/{external_id} | | ✅ | |
| S14 | 중앙 빈 상태 (필터 조합) | `period=day&league_id=2` 빈 mock | "조건에 경기 없습니다" + reset 버튼 → 기본값 복귀 | ✅ | ✅ | |
| S15 | 중앙 에러 (5xx) | MSW 5xx | 에러 박스 + "다시 시도" / 다른 패널 영향 X | | ✅ | |
| S16 | 우측 상단 standings — 리그 변경 | select UCL | fetch league_id=2 / row 갱신 | | ✅ | ✅ |
| S17 | 우측 상단 standings — 컵 대회 빈 응답 | select Carabao mock 빈 | "토너먼트 형식" 빈 카피 | | ✅ | |
| S18 | 우측 하단 top players — metric 변경 | metric=assists | fetch metric=assists / row 갱신 | | ✅ | |
| S19 | 우측 하단 top players — league 변경 | league UEL | fetch league_id=3 / row 갱신 | | ✅ | |
| S20 | standings row 클릭 → 팀 페이지 | row click | URL = /teams/{slug} | | ✅ | |
| S21 | top player row 클릭 → 선수 페이지 | row click | URL = /players/{slug} | | ✅ | |
| S22 | 패널 내부 스크롤 — 시각 스크롤바 숨김 | computed style | `scrollbar-width: none` / `::-webkit-scrollbar { display: none }` | ✅ | | |
| S23 | 패널 내부 스크롤 — 휠 동작 정상 | wheel event on panel | scrollTop 증가 | | ✅ | |
| S24 | 패널 내부 스크롤 — fade-out gradient | 스크롤 가능 패널 | overlay element 존재 | ✅ | | |
| S25 | 다크/라이트 토글 | header 토글 click | html class `dark` 토글 + localStorage `theme` | | ✅ | |
| S26 | 시스템 prefers-color-scheme: dark | 새 세션 + dark prefer | 초기 dark 적용 | | ✅ | |
| S27 | 우상단 비로그인 → "로그인" 표시 | localStorage mockRole=public | "로그인" 버튼 visible | | ✅ | |
| S28 | STREAMER role → 상단 탭 "방송" 추가 | mockRole=STREAMER | nav 에 "방송" 탭 표시 | | ✅ | |
| S29 | USER role → 상단 "방송" 비표시 | mockRole=USER | 탭 없음 | ✅ | | |
| S30 | 큐브 면 빈 데이터 (뉴스 0건) | mock empty=true | "오늘 EPL 관련 뉴스가 없습니다" + 6h 갱신 안내 | | ✅ | |
| S31 | 시즌 휴식기 (오늘/이번주/달 0건) | fixtures empty | 빈 상태 + "다음 경기일정 보기" 버튼 → /fixtures | | ✅ | |
| S32 | 페이지 polling 없음 | 30초 대기 | fetch 호출 횟수 == 초기 1세트만 (변동 X) | | ✅ | |
| S33 | LCP < 1.5s | trace | LCP 측정 (CI 기준 < 2.0s margin) | | ✅ | |
| S34 | 접근성 — 큐브 aria 속성 | DOM | role=region, aria-roledescription=carousel, 각 면 group | ✅ | | |
| S35 | 접근성 — 모든 클릭 element keyboard 도달 | tab cycle | 모든 카드/탭/select 에 tab 도달 가능 | | ✅ | |
| S36 | 응답 shape — zod 검증 (integration) | 실 BE 응답 | 모든 7개 endpoint zod parse 성공 | | | ✅ |
| S37 | 한글 fallback — name_ko=null → 영문 표시 | mock name_ko=null 카드 | 영문 이름 렌더 | ✅ | | |
| S38 | 리그 배지 색상 적용 | EPL 카드 | computed style `background-color` = palette EPL primary | | ✅ | |
| S39 | KST 시간 표기 | 카드 kickoff | "19:00" 형식 (KST), 상대시간 "3시간 전" | ✅ | | |
| S40 | 새로고침 — 필터 기본값 복귀 | 필터 변경 후 F5 | URL 쿼리 없음, store 기본값 (day / 전체) | | ✅ | |

총 40 시나리오. L1 = 12, L2 = 28, L3 = 4. (일부 중복)

---

## 2. L1 — Vitest (component / unit)

대상 컴포넌트별 테스트 파일:

| 파일 | 시나리오 |
|---|---|
| `tests/unit/components/home/CubeCarousel.spec.ts` | S06 S07 S34 |
| `tests/unit/components/home/FixtureCard.spec.ts` | S37 S39 |
| `tests/unit/components/common/PanelScroll.spec.ts` | S22 S24 |
| `tests/unit/components/home/StandingsBlock.spec.ts` | S11 (단위) |
| `tests/unit/components/home/EmptyState.spec.ts` | S14 (단위) |
| `tests/unit/components/common/AppHeader.spec.ts` | S29 |
| `tests/unit/lib/format/datetime.spec.ts` | KST 변환 / 상대시간 |
| `tests/unit/lib/league-colors.spec.ts` | id→slug 매핑 |
| `tests/unit/stores/home.spec.ts` | store actions (filter/fetch/cube rotate state) |

L1 통과 게이트: vitest exit 0.

---

## 3. L2 — Playwright (mock mode)

설정:
- `playwright.config.ts` 에 `mock` project (`baseURL = http://localhost:5173`, MSW 활성화)
- 시작 명령: `VITE_USE_MOCK=true npm run dev`

테스트 파일: `frontend/e2e/main-home.spec.ts`

```ts
test.describe('main-home (mock)', () => {
  test('S01 cold load — 3패널 정상', async ({ page }) => { ... })
  test('S02 페이지 스크롤 금지', async ({ page }) => { ... })
  test('S03 큐브 자동 회전 10초', async ({ page }) => { ... })
  test('S04 큐브 hover 정지', async ({ page }) => { ... })
  // ...
})
```

mock data 시나리오별 분기: MSW handler 에 `?scenario=empty | error | normal` 쿼리 분기 또는 별도 handler 그룹.

L2 통과 게이트:
- 모든 ✅ in L2 통과
- screenshot 회귀 (3D 큐브 0면 / 패널 layout) baseline 저장
- console error 0 / network 5xx 0

---

## 4. L3 — Playwright (integration)

`integration` 라이프사이클 (별 branch `fe-feat-integration-main-home`) 에서 추가.

테스트 파일: `frontend/e2e-integration/main-home.spec.ts`

- 환경: Vercel preview deploy URL
- BE: prod (읽기만)
- zod 검증: 응답을 `types/home.ts` 의 zod 스키마로 parse. 실패 시 fail.

| 시나리오 | 검증 |
|---|---|
| S01 | 실 데이터로 3패널 fit 확인 |
| S11 | EPL 필터 변경 후 카드 실 데이터 |
| S16 | UCL standings 실 데이터 |
| S36 | **모든 7개 endpoint 응답 zod schema 통과** |

L3 통과 게이트: 위 모두 exit 0 + zod schema fail 0 + 데이터 변경 (POST/PUT) 호출 0 회.

---

## 5. L4 — Prod smoke

`frontend/e2e-smoke/main-home.spec.ts`:
- 홈 진입 → 200 응답
- `[data-testid="fixture-list"]` 또는 빈 상태 카피 둘 중 하나 visible
- console error 0

---

## 6. 테스트 데이터 (mock 시나리오 분기)

| 쿼리 파라미터 / 헤더 | 동작 |
|---|---|
| `?scenario=normal` (default) | 모든 패널 정상 5건 / 8건 |
| `?scenario=empty` | 빈 응답 (S14 S17 S30 S31) |
| `?scenario=error` | 5xx (S15) |
| `?scenario=null-ko` | name_ko 가 null (S37) |

Playwright 테스트는 `page.goto('/?scenario=empty')` 같이 진입. MSW handler 가 `URL.searchParams.scenario` 를 읽어 분기.

---

## 7. 통과 기준 (요약)

| 게이트 | 조건 |
|---|---|
| Mock 머지 | L1 exit 0 + L2 exit 0 + lint/type/build pass + 번들 회귀 < 10% + reviewer APPROVE |
| Integration 머지 | 위 + L3 exit 0 + zod schema pass + 데이터 변경 0회 + reviewer APPROVE |
| Prod | L4 통과 (실패 시 알림, 자동 롤백 없음) |

---

## 8. 메모

- 큐브 회전 타이밍 테스트 (S03) 는 flaky 가능 → `page.clock.install()` 또는 `useFakeTimers` 권장 (fe-dev 결정)
- LCP 측정 (S33) 은 CI hardware 변동성 큼 → margin 2.0s 사용
- screenshot 회귀는 다크/라이트 양쪽 baseline 필요
