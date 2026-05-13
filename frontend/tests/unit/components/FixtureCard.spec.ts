import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import FixtureCard from '@/components/home/FixtureCard.vue'
import type { FixtureSummary } from '@/types/home'

function makeFixture(over: Partial<FixtureSummary> = {}): FixtureSummary {
  return {
    external_id: 9001,
    league: { external_id: 39, slug: 'premier-league', name_ko: '프리미어리그', short_name_ko: 'EPL', name: 'Premier League' },
    home: { external_id: 40, slug: 'liverpool', name_ko: '리버풀', short_name_ko: '리버풀', name: 'Liverpool', logo_url: null },
    away: { external_id: 49, slug: 'chelsea', name_ko: '첼시', short_name_ko: '첼시', name: 'Chelsea', logo_url: null },
    kickoff_at: '2026-05-14T10:00:00Z',
    status_short: 'NS',
    goals_home: null,
    goals_away: null,
    ...over,
  }
}

describe('FixtureCard', () => {
  it('shows team name_ko when present', () => {
    const w = mount(FixtureCard, { props: { fixture: makeFixture() } })
    expect(w.text()).toContain('리버풀')
    expect(w.text()).toContain('첼시')
  })
  it('falls back to english name when name_ko is null', () => {
    const fx = makeFixture({
      home: { external_id: 40, slug: 'liverpool', name_ko: null, short_name_ko: null, name: 'Liverpool', logo_url: null },
    })
    const w = mount(FixtureCard, { props: { fixture: fx } })
    expect(w.text()).toContain('Liverpool')
  })
  it('renders KST time for NS', () => {
    const w = mount(FixtureCard, { props: { fixture: makeFixture() } })
    expect(w.text()).toContain('19:00')
  })
  it('renders score for FT', () => {
    const fx = makeFixture({ status_short: 'FT', goals_home: 3, goals_away: 1 })
    const w = mount(FixtureCard, { props: { fixture: fx } })
    expect(w.text()).toContain('3 - 1')
  })
  it('has data-league attribute for theme swap', () => {
    const w = mount(FixtureCard, { props: { fixture: makeFixture() } })
    expect(w.attributes('data-league')).toBe('premier-league')
  })
  it('emits open with id when clicked', async () => {
    const w = mount(FixtureCard, { props: { fixture: makeFixture() } })
    await w.trigger('click')
    expect(w.emitted('open')?.[0]).toEqual([9001])
  })
})
