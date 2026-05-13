import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useHomeStore } from '@/stores/home'

describe('useHomeStore (cube + filter actions)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  it('initial state defaults', () => {
    const s = useHomeStore()
    expect(s.cube.activeFace).toBe(0)
    expect(s.fixtures.filter.period).toBe('day')
    expect(s.fixtures.filter.league_id).toBeNull()
    expect(s.standings.league_id).toBe(39)
    expect(s.topPlayers.metric).toBe('goals')
  })

  it('nextFace cycles 0→1→2→3→0', () => {
    const s = useHomeStore()
    s.nextFace(); expect(s.cube.activeFace).toBe(1)
    s.nextFace(); expect(s.cube.activeFace).toBe(2)
    s.nextFace(); expect(s.cube.activeFace).toBe(3)
    s.nextFace(); expect(s.cube.activeFace).toBe(0)
  })

  it('setFace updates activeFace', () => {
    const s = useHomeStore()
    s.setFace(2)
    expect(s.cube.activeFace).toBe(2)
  })

  it('pauseAutoRotate clears timer', () => {
    const s = useHomeStore()
    s.startAutoRotate()
    expect(s.cube.timerHandle).not.toBeNull()
    s.pauseAutoRotate()
    expect(s.cube.paused).toBe(true)
    expect(s.cube.timerHandle).toBeNull()
  })

  it('resetFixtureFilters returns to defaults', () => {
    const s = useHomeStore()
    s.fixtures.filter.league_id = 39
    s.fixtures.filter.period = 'week'
    // stub fetch
    s.fetchFixtures = vi.fn() as any
    s.resetFixtureFilters()
    expect(s.fixtures.filter.league_id).toBeNull()
    expect(s.fixtures.filter.period).toBe('day')
  })
})
