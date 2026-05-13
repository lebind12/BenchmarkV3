import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import GoalHistoryInline from '@/components/fixture/GoalHistoryInline.vue'
import type { GoalEventSummary } from '@/types/fixtureDetail'

const player = (id: number, name: string): GoalEventSummary['scorer'] => ({
  external_id: id,
  slug: `p${id}`,
  name,
  name_ko: null,
  photo_url: null,
})

describe('GoalHistoryInline', () => {
  it('renders each goal with minute label', () => {
    const events: GoalEventSummary[] = [
      { minute: 23, extra: null, scorer: player(1, 'A'), team_external_id: 1, type: 'normal' },
      { minute: 45, extra: 2, scorer: player(2, 'B'), team_external_id: 2, type: 'penalty' },
    ]
    const w = mount(GoalHistoryInline, { props: { events } })
    expect(w.text()).toContain("23'")
    expect(w.text()).toContain("45+2'")
    expect(w.text()).toContain('(PEN)')
  })

  it('renders nothing when events empty', () => {
    const w = mount(GoalHistoryInline, { props: { events: [] } })
    expect(w.find('[data-testid=goal-history]').exists()).toBe(false)
  })
})
