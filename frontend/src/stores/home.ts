import { defineStore } from 'pinia'
import { homeApi } from '@/lib/api/home'
import type {
  AsyncSlice,
  FixtureSummary,
  HotPlayer,
  Injury,
  MetricKey,
  NewsItem,
  Period,
  StandingRow,
  TopPlayerRow,
  Transfer,
} from '@/types/home'

const ROTATE_MS = 10_000

function newSlice<T>(): AsyncSlice<T> {
  return { status: 'idle', value: null, error: null, fetchedAt: null }
}

export const useHomeStore = defineStore('home', {
  state: () => ({
    cube: {
      activeFace: 0 as 0 | 1 | 2 | 3,
      paused: false,
      timerHandle: null as ReturnType<typeof setInterval> | null,
    },
    news: newSlice<NewsItem[]>(),
    hot: newSlice<HotPlayer[]>(),
    transfers: newSlice<Transfer[]>(),
    injuries: newSlice<Injury[]>(),
    fixtures: {
      filter: { league_id: null as number | null, period: 'day' as Period },
      data: newSlice<FixtureSummary[]>(),
    },
    standings: {
      league_id: 39,
      data: newSlice<StandingRow[]>(),
    },
    topPlayers: {
      league_id: 39,
      metric: 'goals' as MetricKey,
      data: newSlice<TopPlayerRow[]>(),
    },
  }),
  actions: {
    async bootstrap() {
      await Promise.all([
        this.fetchNews(),
        this.fetchHot(),
        this.fetchTransfers(),
        this.fetchInjuries(),
        this.fetchFixtures(),
        this.fetchStandings(),
        this.fetchTopPlayers(),
      ])
      this.startAutoRotate()
    },
    async _runSlice<T>(slice: AsyncSlice<T>, fn: () => Promise<T>) {
      slice.status = 'loading'
      slice.error = null
      try {
        slice.value = await fn()
        slice.status = 'ok'
        slice.fetchedAt = Date.now()
      } catch (e: any) {
        slice.status = 'error'
        slice.error = String(e?.message ?? e)
      }
    },
    fetchNews() { return this._runSlice(this.news, async () => (await homeApi.news()).items) },
    fetchHot() { return this._runSlice(this.hot, async () => (await homeApi.hot()).items) },
    fetchTransfers() { return this._runSlice(this.transfers, async () => (await homeApi.transfers()).items) },
    fetchInjuries() { return this._runSlice(this.injuries, async () => (await homeApi.injuries()).items) },
    fetchFixtures() {
      return this._runSlice(this.fixtures.data, async () =>
        (await homeApi.fixtures(this.fixtures.filter.period, this.fixtures.filter.league_id)).items,
      )
    },
    fetchStandings() {
      return this._runSlice(this.standings.data, async () =>
        (await homeApi.standings(this.standings.league_id)).rows,
      )
    },
    fetchTopPlayers() {
      return this._runSlice(this.topPlayers.data, async () =>
        (await homeApi.topPlayers(this.topPlayers.league_id, this.topPlayers.metric)).rows,
      )
    },
    setLeagueFilter(id: number | null) {
      this.fixtures.filter.league_id = id
      this.fetchFixtures()
    },
    setPeriod(p: Period) {
      this.fixtures.filter.period = p
      this.fetchFixtures()
    },
    setStandingsLeague(id: number) {
      this.standings.league_id = id
      this.fetchStandings()
    },
    setTopPlayersLeague(id: number) {
      this.topPlayers.league_id = id
      this.fetchTopPlayers()
    },
    setTopPlayersMetric(m: MetricKey) {
      this.topPlayers.metric = m
      this.fetchTopPlayers()
    },
    resetFixtureFilters() {
      this.fixtures.filter = { league_id: null, period: 'day' }
      this.fetchFixtures()
    },

    // Cube auto-rotation
    setFace(i: 0 | 1 | 2 | 3) {
      this.cube.activeFace = i
      this.restartTimer()
    },
    nextFace() {
      this.cube.activeFace = (((this.cube.activeFace + 1) % 4) as 0 | 1 | 2 | 3)
    },
    pauseAutoRotate() {
      this.cube.paused = true
      if (this.cube.timerHandle) {
        clearInterval(this.cube.timerHandle)
        this.cube.timerHandle = null
      }
    },
    resumeAutoRotate() {
      this.cube.paused = false
      this.startAutoRotate()
    },
    startAutoRotate() {
      if (this.cube.timerHandle || this.cube.paused) return
      this.cube.timerHandle = setInterval(() => this.nextFace(), ROTATE_MS)
    },
    restartTimer() {
      if (this.cube.timerHandle) {
        clearInterval(this.cube.timerHandle)
        this.cube.timerHandle = null
      }
      if (!this.cube.paused) this.startAutoRotate()
    },
    teardown() {
      if (this.cube.timerHandle) {
        clearInterval(this.cube.timerHandle)
        this.cube.timerHandle = null
      }
    },
  },
})
