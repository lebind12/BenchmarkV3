import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LineupRow from '@/components/fixture/LineupRow.vue'
import type { LineupPlayer } from '@/types/fixtureDetail'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/players/:slug', name: 'p', component: { template: '<div />' } as never },
  ],
})

const base: LineupPlayer = {
  player: {
    external_id: 1,
    slug: 'salah',
    name: 'Salah',
    name_ko: '살라',
    photo_url: null,
  },
  number: 11,
  position: 'RW',
  grid: null,
  rating: 7.4,
  minutes: 90,
}

describe('LineupRow', () => {
  it('renders number, position and ko name', () => {
    const w = mount(LineupRow, {
      props: { player: base },
      global: { plugins: [router] },
    })
    expect(w.text()).toContain('11')
    expect(w.text()).toContain('RW')
    expect(w.text()).toContain('살라')
  })

  it('shows rating when present', () => {
    const w = mount(LineupRow, {
      props: { player: base },
      global: { plugins: [router] },
    })
    expect(w.find('[data-testid=lineup-rating]').exists()).toBe(true)
    expect(w.text()).toContain('7.4')
  })

  it('hides rating when null', () => {
    const w = mount(LineupRow, {
      props: { player: { ...base, rating: null } },
      global: { plugins: [router] },
    })
    expect(w.find('[data-testid=lineup-rating]').exists()).toBe(false)
  })
})
