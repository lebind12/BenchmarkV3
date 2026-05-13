import type { LeagueRef, TeamRef, PlayerRef } from '@/types/home'

export type FixtureStatus =
  | 'NS'
  | '1H'
  | 'HT'
  | '2H'
  | 'ET'
  | 'BT'
  | 'P'
  | 'PEN'
  | 'FT'
  | 'AET'
  | 'PST'
  | 'CANC'
  | 'SUSP'

export interface GoalEventSummary {
  minute: number
  extra: number | null
  scorer: PlayerRef
  team_external_id: number
  type: 'normal' | 'penalty' | 'own_goal'
}

export interface MatchDetail {
  external_id: number
  league: LeagueRef
  round: string
  status_short: FixtureStatus
  status_long: string
  kickoff_at: string
  venue: { name: string; city: string | null } | null
  referee: string | null
  home: TeamRef
  away: TeamRef
  goals_home: number | null
  goals_away: number | null
  penalty_home: number | null
  penalty_away: number | null
  goal_events: GoalEventSummary[]
}

export type TimelineEventType =
  | 'goal'
  | 'goal_penalty'
  | 'goal_own'
  | 'yellow_card'
  | 'red_card'
  | 'yellow_red'
  | 'substitution'
  | 'var'

export interface TimelineEvent {
  id: string
  minute: number
  extra: number | null
  team_external_id: number
  type: TimelineEventType
  player: PlayerRef
  assist: PlayerRef | null
  player_out: PlayerRef | null
  detail: string | null
}

export interface LineupPlayer {
  player: PlayerRef
  number: number
  position: string
  grid: string | null
  rating: number | null
  minutes: number | null
}

export interface TeamLineup {
  team: TeamRef
  formation: string | null
  coach: { name: string } | null
  start_xi: LineupPlayer[]
  bench: LineupPlayer[]
}

export interface H2HFixture {
  external_id: number
  league: Pick<LeagueRef, 'external_id' | 'slug' | 'short_name_ko' | 'name'>
  kickoff_at: string
  home: TeamRef
  away: TeamRef
  goals_home: number
  goals_away: number
  status_short: FixtureStatus
}

export interface TeamStat {
  team_external_id: number
  possession: number | null
  shots_total: number | null
  shots_on_target: number | null
  passes_total: number | null
  passes_accuracy: number | null
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
  group_name?: string | null
}

export interface LeagueStandingsPayload {
  league: LeagueRef
  season: number
  group_name: string | null
  rows: StandingRowDetail[]
  highlighted_team_ids: [number, number]
}

export type SliceStatus = 'idle' | 'loading' | 'ok' | 'error' | 'not_found'

export interface Slice<T> {
  status: SliceStatus
  value: T | null
  error: string | null
}

export type ActiveTab = 'formation' | 'h2h' | 'stats' | 'standings'
