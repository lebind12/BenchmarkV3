import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MatchHeader from '@/components/fixture/MatchHeader.vue'
import match1 from '@/mocks/data/fixture-detail/match.1000001.json'
import match2 from '@/mocks/data/fixture-detail/match.1000002.json'
import type { MatchDetail } from '@/types/fixtureDetail'

describe('MatchHeader', () => {
  it('renders score for FT match', () => {
    const w = mount(MatchHeader, {
      props: { match: match1 as unknown as MatchDetail },
    })
    expect(w.find('[data-testid=match-score]').text()).toContain('3 - 1')
    expect(w.find('[data-testid=goal-history]').exists()).toBe(true)
  })

  it('renders "vs" + kickoff label for NS match', () => {
    const w = mount(MatchHeader, {
      props: { match: match2 as unknown as MatchDetail },
    })
    expect(w.find('[data-testid=match-score]').text()).toContain('vs')
    expect(w.find('[data-testid=match-score]').text()).toMatch(/kickoff .* KST/)
  })

  it('shows 6h SLA notice', () => {
    const w = mount(MatchHeader, {
      props: { match: match1 as unknown as MatchDetail },
    })
    expect(w.text()).toContain('6시간')
  })

  it('omits null referee from meta', () => {
    const w = mount(MatchHeader, {
      props: { match: match2 as unknown as MatchDetail },
    })
    expect(w.find('[data-testid=match-meta]').text()).not.toContain('null')
  })

  it('falls back to English name when name_ko is missing', () => {
    const m = {
      ...(match1 as unknown as MatchDetail),
      home: { ...(match1 as unknown as MatchDetail).home, name_ko: null },
    }
    const w = mount(MatchHeader, { props: { match: m } })
    expect(w.html()).toContain('Liverpool')
  })
})
