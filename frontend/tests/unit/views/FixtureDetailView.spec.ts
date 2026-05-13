import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import FixtureDetailView from '@/views/FixtureDetailView.vue'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/fixtures/:externalId(\\d+)',
        name: 'fixture-detail',
        component: FixtureDetailView,
      },
      {
        path: '/not-found',
        name: 'not-found',
        component: { template: '<div data-testid="not-found">404</div>' } as never,
      },
      {
        path: '/players/:slug',
        name: 'player-detail',
        component: { template: '<div />' } as never,
      },
      {
        path: '/teams/:slug',
        name: 'team-detail',
        component: { template: '<div />' } as never,
      },
    ],
  })
}

describe('FixtureDetailView', () => {
  it('binds data-league to root once match loads', async () => {
    const router = makeRouter()
    router.push('/fixtures/1000001')
    await router.isReady()
    const w = mount(FixtureDetailView, {
      global: { plugins: [createPinia(), router] },
    })
    await flushPromises()
    await flushPromises()
    const root = w.find('[data-testid=fixture-detail-root]')
    expect(root.exists()).toBe(true)
    expect(root.attributes('data-league')).toBe('premier-league')
  })

  it('does not have data-league while match still loading', async () => {
    const router = makeRouter()
    router.push('/fixtures/1000001')
    await router.isReady()
    const w = mount(FixtureDetailView, {
      global: { plugins: [createPinia(), router] },
    })
    const root = w.find('[data-testid=fixture-detail-root]')
    expect(root.attributes('data-league')).toBeUndefined()
  })
})
