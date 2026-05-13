import { test, expect } from '@playwright/test'

test.describe('fixture-detail (mock)', () => {
  test('F01 FT 매치 cold load', async ({ page }) => {
    await page.goto('/fixtures/1000001')
    await expect(page.getByTestId('match-header')).toBeVisible()
    await expect(page.getByTestId('events-timeline')).toBeVisible()
    await expect(page.getByTestId('center-tabs')).toBeVisible()
    await expect(page.getByTestId('lineups-right')).toBeVisible()
    await expect(page.getByTestId('match-score')).toContainText('3 - 1')
  })

  test('F02 page body overflow hidden + no footer', async ({ page }) => {
    await page.goto('/fixtures/1000001')
    const bodyOverflow = await page.evaluate(
      () => getComputedStyle(document.body).overflow,
    )
    expect(bodyOverflow).toBe('hidden')
    expect(await page.locator('footer').count()).toBe(0)
  })

  test('F04 NS 매치 placeholder', async ({ page }) => {
    await page.goto('/fixtures/1000002')
    await expect(page.getByTestId('match-score')).toContainText('vs')
    await expect(page.getByTestId('events-empty-ns')).toBeVisible()
    await expect(page.getByTestId('lineup-empty').first()).toBeVisible()
  })

  test('F09 매치 미발견 → /not-found redirect', async ({ page }) => {
    await page.goto('/fixtures/1000099')
    await page.waitForURL('**/not-found')
    await expect(page.getByTestId('not-found')).toBeVisible()
  })

  test('F18 default 탭 = 포메이션, URL 쿼리 없음', async ({ page }) => {
    await page.goto('/fixtures/1000001')
    await expect(page.getByTestId('tab-formation')).toBeVisible()
    expect(page.url()).not.toContain('tab=')
  })

  test('F19 서브탭 변경 → URL 쿼리 반영', async ({ page }) => {
    await page.goto('/fixtures/1000001')
    await page.locator('button[data-tab="h2h"]').click()
    await expect(page.getByTestId('tab-h2h')).toBeVisible()
    expect(page.url()).toContain('tab=h2h')
  })

  test('F20 URL ?tab=stats 새로고침 시 stats 탭 복원', async ({ page }) => {
    await page.goto('/fixtures/1000001?tab=stats')
    await expect(page.getByTestId('tab-stats')).toBeVisible()
  })

  test('F37/F38 라인업 시작 11 + 벤치 토글', async ({ page }) => {
    await page.goto('/fixtures/1000001')
    const home = page.getByTestId('lineup-panel-home')
    await expect(home).toBeVisible()
    const startRows = home.getByTestId('lineup-row')
    await expect(startRows).toHaveCount(11)
    const toggle = page.getByTestId('bench-toggle-home')
    await expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await toggle.click()
    await expect(toggle).toHaveAttribute('aria-expanded', 'true')
    await expect(page.getByTestId('bench-list-home')).toBeVisible()
  })

  test('F58/F61 league 동적 테마 — root data-league swap', async ({ page }) => {
    await page.goto('/fixtures/1000001')
    await expect(page.getByTestId('fixture-detail-root')).toHaveAttribute(
      'data-league',
      'premier-league',
    )
    await page.goto('/fixtures/1000007')
    await expect(page.getByTestId('fixture-detail-root')).toHaveAttribute(
      'data-league',
      'champions-league',
    )
  })

  test('F46 polling 없음 — 추가 fetch 발생 X', async ({ page }) => {
    const requests: string[] = []
    page.on('request', (r) => {
      if (r.url().includes('/api/v1/fixtures/')) requests.push(r.url())
    })
    await page.goto('/fixtures/1000001')
    const initial = requests.length
    await page.waitForTimeout(3000)
    expect(requests.length).toBe(initial)
  })
})
