// Shared response types (mock SSOT). Mirrors devplan §6.
export type LeagueSlug =
  | 'premier-league'
  | 'champions-league'
  | 'europa-league'
  | 'carabao-cup'
  | 'fa-cup'

export interface LeagueRef {
  external_id: number
  slug: LeagueSlug
  name_ko: string | null
  short_name_ko: string | null
  name: string
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
  team: Pick<TeamRef, 'external_id' | 'slug' | 'name_ko' | 'name' | 'logo_url'>
  league: Pick<LeagueRef, 'external_id' | 'slug' | 'name_ko' | 'name'>
}

export interface NewsItem {
  id: string
  title_ko: string | null
  title: string
  summary_ko: string | null
  source: string
  url: string
  thumbnail_url: string | null
  published_at: string
}

export interface HotPlayer {
  player: PlayerRef
  goals: number
  assists: number
  score: number
}

export interface Transfer {
  id: string
  player: PlayerRef
  from_team: TeamRef
  to_team: TeamRef
  transfer_date: string
  fee: string | null
}

export interface Injury {
  id: string
  player: PlayerRef
  injury_type: string
  expected_return: string | null
  reported_at: string
}

export type FixtureStatus =
  | 'NS'
  | '1H'
  | 'HT'
  | '2H'
  | 'ET'
  | 'PEN'
  | 'FT'
  | 'AET'
  | 'PST'
  | 'CANC'

export interface FixtureSummary {
  external_id: number
  league: LeagueRef
  home: TeamRef
  away: TeamRef
  kickoff_at: string
  status_short: FixtureStatus
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

export type MetricKey = 'goals' | 'assists' | 'yellow_cards' | 'red_cards'
export type Period = 'day' | 'week' | 'month'

export interface AsyncSlice<T> {
  status: 'idle' | 'loading' | 'ok' | 'error'
  value: T | null
  error: string | null
  fetchedAt: number | null
}
