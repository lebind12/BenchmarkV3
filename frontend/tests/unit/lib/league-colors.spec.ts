import { describe, expect, it } from 'vitest'
import { LEAGUE_ID_TO_SLUG, leagueVar, slugFromId } from '@/lib/league-colors'

describe('league-colors', () => {
  it('maps known league ids to slugs', () => {
    expect(slugFromId(39)).toBe('premier-league')
    expect(slugFromId(2)).toBe('champions-league')
    expect(slugFromId(3)).toBe('europa-league')
    expect(slugFromId(48)).toBe('carabao-cup')
    expect(slugFromId(45)).toBe('fa-cup')
  })
  it('returns null for unknown id', () => {
    expect(slugFromId(9999)).toBeNull()
    expect(slugFromId(null)).toBeNull()
  })
  it('leagueVar formats CSS var', () => {
    expect(leagueVar('premier-league', 'primary')).toBe('var(--league-epl-primary)')
    expect(leagueVar('champions-league', 'on-primary')).toBe('var(--league-ucl-on-primary)')
  })
  it('leagueVar falls back to muted for null slug', () => {
    expect(leagueVar(null, 'primary')).toContain('--muted')
  })
  it('covers all 5 league ids', () => {
    expect(Object.keys(LEAGUE_ID_TO_SLUG)).toHaveLength(5)
  })
})
