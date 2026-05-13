import type { LeagueSlug } from '@/types/home'

export const LEAGUE_ID_TO_SLUG: Record<number, LeagueSlug> = {
  39: 'premier-league',
  2: 'champions-league',
  3: 'europa-league',
  48: 'carabao-cup',
  45: 'fa-cup',
}

export const LEAGUE_TOKEN: Record<LeagueSlug, string> = {
  'premier-league': 'epl',
  'champions-league': 'ucl',
  'europa-league': 'uel',
  'carabao-cup': 'carabao',
  'fa-cup': 'fa',
}

export const LEAGUE_SHORT_KO: Record<LeagueSlug, string> = {
  'premier-league': 'EPL',
  'champions-league': 'UCL',
  'europa-league': 'UEL',
  'carabao-cup': '카라바오',
  'fa-cup': 'FA',
}

export function slugFromId(id: number | null | undefined): LeagueSlug | null {
  if (id == null) return null
  return LEAGUE_ID_TO_SLUG[id] ?? null
}

export function leagueVar(
  slug: LeagueSlug | null,
  kind: 'primary' | 'secondary' | 'accent' | 'on-primary',
): string {
  if (!slug) return 'var(--muted, #888)'
  const token = LEAGUE_TOKEN[slug]
  return `var(--league-${token}-${kind})`
}
