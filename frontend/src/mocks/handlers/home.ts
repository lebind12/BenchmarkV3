import { http, HttpResponse } from 'msw'
import news from '@/mocks/data/home/news.json'
import hot from '@/mocks/data/home/hot.json'
import transfers from '@/mocks/data/home/transfers.json'
import injuries from '@/mocks/data/home/injuries.json'
import fixtures from '@/mocks/data/home/fixtures.json'
import standings from '@/mocks/data/home/standings.json'
import topPlayers from '@/mocks/data/home/top_players.json'

type Scenario = 'normal' | 'empty' | 'error' | 'null-ko'

function getScenario(req: Request): Scenario {
  const url = new URL(req.url)
  const s = url.searchParams.get('scenario')
  if (s === 'empty' || s === 'error' || s === 'null-ko') return s
  // page-level scenario carried by referrer (page.goto('/?scenario=empty'))
  const refer = req.referrer ?? ''
  try {
    const u = new URL(refer)
    const rs = u.searchParams.get('scenario')
    if (rs === 'empty' || rs === 'error' || rs === 'null-ko') return rs
  } catch {
    /* ignore */
  }
  return 'normal'
}

function maybeError(scenario: Scenario, body: unknown): Response {
  if (scenario === 'error') {
    return HttpResponse.json({ error: 'mock error' }, { status: 500 })
  }
  return HttpResponse.json(body as Record<string, unknown>)
}

function nullifyKo(items: any[]): any[] {
  return items.map((it) => JSON.parse(JSON.stringify(it).replace(/"name_ko":"[^"]*"/g, '"name_ko":null')))
}

export const homeHandlers = [
  http.get('/api/v1/home/news', ({ request }) => {
    const s = getScenario(request)
    if (s === 'empty') return HttpResponse.json({ items: [] })
    return maybeError(s, news)
  }),
  http.get('/api/v1/home/hot-players', ({ request }) => {
    const s = getScenario(request)
    if (s === 'empty') return HttpResponse.json({ items: [] })
    if (s === 'null-ko') return HttpResponse.json({ items: nullifyKo(hot.items) })
    return maybeError(s, hot)
  }),
  http.get('/api/v1/home/transfers', ({ request }) => {
    const s = getScenario(request)
    if (s === 'empty') return HttpResponse.json({ items: [] })
    return maybeError(s, transfers)
  }),
  http.get('/api/v1/home/injuries', ({ request }) => {
    const s = getScenario(request)
    if (s === 'empty') return HttpResponse.json({ items: [] })
    return maybeError(s, injuries)
  }),
  http.get('/api/v1/home/fixtures', ({ request }) => {
    const s = getScenario(request)
    const url = new URL(request.url)
    const leagueId = url.searchParams.get('league_id')
    const period = (url.searchParams.get('period') ?? 'day') as 'day' | 'week' | 'month'

    if (s === 'empty') {
      return HttpResponse.json({ items: [], filters_applied: { period, league_id: leagueId ? Number(leagueId) : undefined } })
    }
    if (s === 'error') {
      return HttpResponse.json({ error: 'mock' }, { status: 500 })
    }

    let items = fixtures.items as any[]
    const PERIODS = ['day', 'week', 'month'] as const
    const periodIdx = PERIODS.indexOf(period)
    items = items.filter((it) => PERIODS.indexOf(it._period) <= periodIdx)
    if (leagueId) {
      items = items.filter((it) => String(it.league.external_id) === leagueId)
    }
    // strip internal _period
    const out = items.map(({ _period, ...rest }) => rest)
    return HttpResponse.json({
      items: out,
      filters_applied: { period, league_id: leagueId ? Number(leagueId) : undefined },
    })
  }),
  http.get('/api/v1/home/standings', ({ request }) => {
    const s = getScenario(request)
    const url = new URL(request.url)
    const id = url.searchParams.get('league_id') ?? '39'
    if (s === 'error') return HttpResponse.json({ error: 'mock' }, { status: 500 })
    const dict = standings as any
    return HttpResponse.json(dict[id] ?? { league: null, season: null, rows: [] })
  }),
  http.get('/api/v1/home/top-players', ({ request }) => {
    const s = getScenario(request)
    const url = new URL(request.url)
    const id = url.searchParams.get('league_id') ?? '39'
    const metric = url.searchParams.get('metric') ?? 'goals'
    if (s === 'error') return HttpResponse.json({ error: 'mock' }, { status: 500 })
    const dict = topPlayers as any
    const rows = dict[id]?.[metric] ?? []
    return HttpResponse.json({
      league: rows[0]?.player?.league ?? null,
      season: 2025,
      metric,
      rows,
    })
  }),
]
