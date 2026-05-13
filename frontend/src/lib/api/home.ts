import type {
  FixtureSummary,
  HotPlayer,
  Injury,
  LeagueRef,
  MetricKey,
  NewsItem,
  Period,
  StandingRow,
  TopPlayerRow,
  Transfer,
} from '@/types/home'

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as T
}

export const homeApi = {
  news: () => getJson<{ items: NewsItem[] }>('/api/v1/home/news'),
  hot:  () => getJson<{ items: HotPlayer[] }>('/api/v1/home/hot-players'),
  transfers: () => getJson<{ items: Transfer[] }>('/api/v1/home/transfers'),
  injuries:  () => getJson<{ items: Injury[] }>('/api/v1/home/injuries'),

  fixtures: (period: Period, leagueId: number | null) => {
    const u = new URL('/api/v1/home/fixtures', window.location.origin)
    u.searchParams.set('period', period)
    if (leagueId != null) u.searchParams.set('league_id', String(leagueId))
    return getJson<{
      items: FixtureSummary[]
      filters_applied: { period: Period; league_id?: number }
    }>(u.pathname + '?' + u.searchParams.toString())
  },

  standings: (leagueId: number) =>
    getJson<{ league: LeagueRef | null; season: number | null; rows: StandingRow[] }>(
      `/api/v1/home/standings?league_id=${leagueId}`,
    ),

  topPlayers: (leagueId: number, metric: MetricKey) =>
    getJson<{ league: LeagueRef | null; season: number; metric: MetricKey; rows: TopPlayerRow[] }>(
      `/api/v1/home/top-players?league_id=${leagueId}&metric=${metric}`,
    ),
}
