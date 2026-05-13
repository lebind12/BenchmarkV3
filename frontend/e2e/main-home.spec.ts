import { test, expect } from '@playwright/test'

test.describe('main-home (mock mode)', () => {
  test.beforeEach(async ({ page }) => {
    // ensure default mock role
    await page.addInitScript(() => {
      try { localStorage.removeItem('mockRole') } catch {}
    })
  })

  test('S01 cold load — 3-panel grid renders with data', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('home-view')).toBeVisible()
    await expect(page.getByTestId('center-panel')).toBeVisible()
    await expect(page.getByTestId('right-panel')).toBeVisible()
    await expect(page.getByTestId('cube')).toBeVisible()
    // Fixtures arrive
    await expect(page.getByTestId(/^fixture-card-/).first()).toBeVisible({ timeout: 5000 })
    // Standings arrive
    await expect(page.getByTestId('standings-block')).toBeVisible()
    // Top players arrive
    await expect(page.getByTestId('top-players-block')).toBeVisible()
  })

  test('S02 page itself does not scroll', async ({ page }) => {
    await page.goto('/')
    const overflow = await page.evaluate(() => getComputedStyle(document.body).overflow)
    expect(overflow).toBe('hidden')
    const footer = await page.$('footer')
    expect(footer).toBeNull()
  })

  test('S06 cube dot click moves activeFace', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('cube-dot-2').click()
    await expect(page.getByTestId('cube-dot-2')).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByTestId('cube-face-2')).toHaveAttribute('aria-hidden', 'false')
    await expect(page.getByTestId('cube-face-0')).toHaveAttribute('aria-hidden', 'true')
  })

  test('S11 center league filter — clicking EPL refetches with league_id=39', async ({ page }) => {
    await page.goto('/')
    const reqPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/home/fixtures') && req.url().includes('league_id=39'),
    )
    await page.getByTestId('league-tab-39').click()
    const req = await reqPromise
    expect(req.url()).toContain('league_id=39')
    await expect(page.getByTestId('league-tab-39')).toHaveAttribute('aria-selected', 'true')
  })

  test('S12 period toggle — switching to 주 changes the query', async ({ page }) => {
    await page.goto('/')
    const reqPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/home/fixtures') && req.url().includes('period=week'),
    )
    await page.getByTestId('period-week').click()
    await reqPromise
  })

  test('S13 fixture card click navigates to fixture detail', async ({ page }) => {
    await page.goto('/')
    const first = page.getByTestId(/^fixture-card-/).first()
    await first.waitFor()
    const tid = await first.getAttribute('data-testid')
    const id = tid!.replace('fixture-card-', '')
    await first.click()
    await expect(page).toHaveURL(new RegExp(`/fixtures/${id}$`))
  })

  test('S14 empty fixtures — empty state with reset button', async ({ page }) => {
    await page.goto('/?scenario=empty')
    await expect(page.getByText('선택한 조건에 경기가 없습니다')).toBeVisible({ timeout: 5000 })
    await expect(page.getByTestId('fixtures-reset')).toBeVisible()
  })

  test('S16 standings — switching to UCL fetches league_id=2', async ({ page }) => {
    await page.goto('/')
    const reqPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/home/standings') && req.url().includes('league_id=2'),
    )
    await page.getByTestId('standings-league-select').selectOption('2')
    await reqPromise
  })

  test('S18 top-players — metric change fetches assists', async ({ page }) => {
    await page.goto('/')
    const reqPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/home/top-players') && req.url().includes('metric=assists'),
    )
    await page.getByTestId('topp-metric-select').selectOption('assists')
    await reqPromise
  })

  test('S20 standings row click navigates to team page', async ({ page }) => {
    await page.goto('/')
    const row = page.getByTestId('standings-row-liverpool')
    await row.waitFor()
    await row.click()
    await expect(page).toHaveURL(/\/teams\/liverpool$/)
  })

  test('S25 dark/light theme toggle', async ({ page }) => {
    await page.goto('/')
    const before = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    await page.getByTestId('theme-toggle').click()
    const after = await page.evaluate(() => document.documentElement.classList.contains('dark'))
    expect(after).not.toBe(before)
    const stored = await page.evaluate(() => localStorage.getItem('theme'))
    expect(stored === 'dark' || stored === 'light').toBe(true)
  })

  test('S27 public role shows 로그인 button', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByTestId('auth-login')).toBeVisible()
  })

  test('S28 STREAMER role shows 방송 tab', async ({ page }) => {
    await page.addInitScript(() => { localStorage.setItem('mockRole', 'STREAMER') })
    await page.goto('/')
    await expect(page.getByTestId('nav-방송')).toBeVisible()
  })

  test('S34 cube accessibility attributes', async ({ page }) => {
    await page.goto('/')
    const region = page.locator('[role="region"][aria-roledescription="carousel"]')
    await expect(region).toBeVisible()
    await expect(region).toHaveAttribute('aria-label', '홈 큐브')
  })
})
