import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import FormationHalf from '@/components/fixture/tabs/FormationHalf.vue'
import lineups1 from '@/mocks/data/fixture-detail/lineups.1000001.json'
import type { TeamLineup } from '@/types/fixtureDetail'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/players/:slug', name: 'p', component: { template: '<div />' } as never }],
})

describe('FormationHalf', () => {
  it('renders 11 nodes for 4-3-3', () => {
    const home = lineups1.home as unknown as TeamLineup
    const w = mount(FormationHalf, {
      props: { lineup: home, side: 'home' },
      global: { plugins: [router] },
    })
    expect(w.findAll('[data-testid=formation-node-home]').length).toBe(11)
  })

  it('uses fallback grid when formation null but xi present', () => {
    const home = lineups1.home as unknown as TeamLineup
    const fallback: TeamLineup = { ...home, formation: null }
    const w = mount(FormationHalf, {
      props: { lineup: fallback, side: 'home' },
      global: { plugins: [router] },
    })
    expect(w.find('[data-testid=formation-fallback]').exists()).toBe(true)
  })
})
