import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFixtureDetailStore } from '@/stores/fixtureDetail'

describe('useFixtureDetailStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('bootstrap loads match/events/lineups in parallel', async () => {
    const store = useFixtureDetailStore()
    await store.bootstrap(1000001)
    expect(store.match.status).toBe('ok')
    expect(store.events.status).toBe('ok')
    expect(store.lineups.status).toBe('ok')
    expect(store.h2h.status).toBe('idle')
    expect(store.statistics.status).toBe('idle')
    expect(store.standings.status).toBe('idle')
  })

  it('setTab triggers lazy fetch only once', async () => {
    const store = useFixtureDetailStore()
    await store.bootstrap(1000001)
    expect(store.statistics.status).toBe('idle')
    await store.setTab('stats')
    expect(store.statistics.status).toBe('ok')
    expect(store.activeTab).toBe('stats')
  })

  it('bootstrap to 1000099 marks match as not_found', async () => {
    const store = useFixtureDetailStore()
    await store.bootstrap(1000099)
    expect(store.match.status).toBe('not_found')
  })

  it('toggleBench flips per-team state', async () => {
    const store = useFixtureDetailStore()
    expect(store.benchExpanded.home).toBe(false)
    store.toggleBench('home')
    expect(store.benchExpanded.home).toBe(true)
    expect(store.benchExpanded.away).toBe(false)
  })
})
