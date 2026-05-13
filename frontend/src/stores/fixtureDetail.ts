import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ActiveTab,
  H2HFixture,
  LeagueStandingsPayload,
  MatchDetail,
  Slice,
  TeamLineup,
  TeamStat,
  TimelineEvent,
} from '@/types/fixtureDetail'
import {
  NotFoundError,
  getMatch,
  getEvents,
  getLineups,
  getH2H,
  getStatistics,
  getLeagueStandings,
} from '@/lib/api/fixtureDetail'

function idle<T>(): Slice<T> {
  return { status: 'idle', value: null, error: null }
}

export const useFixtureDetailStore = defineStore('fixtureDetail', () => {
  const externalId = ref<number | null>(null)

  const match = ref<Slice<MatchDetail>>(idle())
  const events = ref<Slice<TimelineEvent[]>>(idle())
  const lineups = ref<Slice<{ home: TeamLineup; away: TeamLineup }>>(idle())
  const h2h = ref<Slice<H2HFixture[]>>(idle())
  const statistics = ref<Slice<{ home: TeamStat; away: TeamStat }>>(idle())
  const standings = ref<Slice<LeagueStandingsPayload>>(idle())

  const activeTab = ref<ActiveTab>('formation')
  const benchExpanded = ref<{ home: boolean; away: boolean }>({
    home: false,
    away: false,
  })

  const leagueSlug = computed(() => match.value.value?.league.slug ?? null)
  const leagueExternalId = computed(
    () => match.value.value?.league.external_id ?? null,
  )

  async function load<T>(slice: { value: Slice<T> }, fn: () => Promise<T>) {
    slice.value = { status: 'loading', value: null, error: null }
    try {
      const v = await fn()
      slice.value = { status: 'ok', value: v, error: null }
    } catch (err) {
      if (err instanceof NotFoundError) {
        slice.value = { status: 'not_found', value: null, error: 'not_found' }
      } else {
        slice.value = {
          status: 'error',
          value: null,
          error: (err as Error).message,
        }
      }
    }
  }

  async function bootstrap(id: number, tab: ActiveTab = 'formation') {
    externalId.value = id
    activeTab.value = tab
    match.value = idle()
    events.value = idle()
    lineups.value = idle()
    h2h.value = idle()
    statistics.value = idle()
    standings.value = idle()
    await Promise.all([
      load(
        { get value() { return match.value }, set value(v) { match.value = v } },
        () => getMatch(id),
      ),
      load(
        { get value() { return events.value }, set value(v) { events.value = v } },
        () => getEvents(id).then((r) => r.events),
      ),
      load(
        { get value() { return lineups.value }, set value(v) { lineups.value = v } },
        () => getLineups(id),
      ),
    ])
    if (tab !== 'formation') await fetchTab(tab)
  }

  async function fetchTab(tab: ActiveTab) {
    if (externalId.value == null) return
    const id = externalId.value
    if (tab === 'h2h' && h2h.value.status === 'idle') {
      await load(
        { get value() { return h2h.value }, set value(v) { h2h.value = v } },
        () => getH2H(id).then((r) => r.h2h),
      )
    } else if (tab === 'stats' && statistics.value.status === 'idle') {
      await load(
        { get value() { return statistics.value }, set value(v) { statistics.value = v } },
        () => getStatistics(id),
      )
    } else if (tab === 'standings' && standings.value.status === 'idle') {
      await load(
        { get value() { return standings.value }, set value(v) { standings.value = v } },
        () => getLeagueStandings(id),
      )
    }
  }

  async function setTab(tab: ActiveTab) {
    activeTab.value = tab
    await fetchTab(tab)
  }

  function toggleBench(team: 'home' | 'away') {
    benchExpanded.value = {
      ...benchExpanded.value,
      [team]: !benchExpanded.value[team],
    }
  }

  return {
    externalId,
    match,
    events,
    lineups,
    h2h,
    statistics,
    standings,
    activeTab,
    benchExpanded,
    leagueSlug,
    leagueExternalId,
    bootstrap,
    fetchTab,
    setTab,
    toggleBench,
  }
})
