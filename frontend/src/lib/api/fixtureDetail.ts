// Mock-mode fetch wrapper for fixture-detail endpoints.
// In mock mode the data is bundled locally; in integration mode the same
// signatures hit the real BE.

import type {
  MatchDetail,
  TimelineEvent,
  TeamLineup,
  H2HFixture,
  TeamStat,
  LeagueStandingsPayload,
} from '@/types/fixtureDetail'

// Use Vite glob import so the mock JSONs are bundled.
const dataFiles = import.meta.glob('@/mocks/data/fixture-detail/*.json', {
  eager: true,
  import: 'default',
}) as Record<string, unknown>

function pick<T>(prefix: string, externalId: number): T | null {
  const key = Object.keys(dataFiles).find((k) =>
    k.endsWith(`/${prefix}.${externalId}.json`),
  )
  return key ? (dataFiles[key] as T) : null
}

const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? 'true') !== 'false'

export class NotFoundError extends Error {
  constructor(public externalId: number) {
    super(`fixture ${externalId} not found`)
  }
}

export class ServerError extends Error {
  constructor(public externalId: number) {
    super(`fixture ${externalId} server error`)
  }
}

async function mockOrFetch<T>(
  prefix: string,
  externalId: number,
  path: string,
): Promise<T> {
  if (externalId === 1000099) throw new NotFoundError(externalId)
  if (externalId === 1000098) throw new ServerError(externalId)
  if (USE_MOCK) {
    // Allow per-id fallback to 1000001 so all scenarios still render.
    const value = pick<T>(prefix, externalId) ?? pick<T>(prefix, 1000001)
    if (!value) throw new NotFoundError(externalId)
    return value
  }
  const res = await fetch(path)
  if (res.status === 404) throw new NotFoundError(externalId)
  if (!res.ok) throw new ServerError(externalId)
  return (await res.json()) as T
}

export function getMatch(externalId: number): Promise<MatchDetail> {
  return mockOrFetch<MatchDetail>(
    'match',
    externalId,
    `/api/v1/fixtures/${externalId}`,
  )
}

export async function getEvents(
  externalId: number,
): Promise<{ events: TimelineEvent[] }> {
  return mockOrFetch<{ events: TimelineEvent[] }>(
    'events',
    externalId,
    `/api/v1/fixtures/${externalId}/events`,
  )
}

export async function getLineups(
  externalId: number,
): Promise<{ home: TeamLineup; away: TeamLineup }> {
  return mockOrFetch<{ home: TeamLineup; away: TeamLineup }>(
    'lineups',
    externalId,
    `/api/v1/fixtures/${externalId}/lineups`,
  )
}

export async function getH2H(
  externalId: number,
): Promise<{ h2h: H2HFixture[] }> {
  return mockOrFetch<{ h2h: H2HFixture[] }>(
    'h2h',
    externalId,
    `/api/v1/fixtures/${externalId}/h2h?limit=5`,
  )
}

export async function getStatistics(
  externalId: number,
): Promise<{ home: TeamStat; away: TeamStat }> {
  return mockOrFetch<{ home: TeamStat; away: TeamStat }>(
    'statistics',
    externalId,
    `/api/v1/fixtures/${externalId}/statistics`,
  )
}

export async function getLeagueStandings(
  externalId: number,
): Promise<LeagueStandingsPayload> {
  return mockOrFetch<LeagueStandingsPayload>(
    'league-standings',
    externalId,
    `/api/v1/fixtures/${externalId}/league-standings`,
  )
}
