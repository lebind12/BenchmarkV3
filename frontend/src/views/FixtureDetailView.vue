<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useFixtureDetailStore } from '@/stores/fixtureDetail'
import type { ActiveTab } from '@/types/fixtureDetail'
import MatchHeader from '@/components/fixture/MatchHeader.vue'
import EventsTimeline from '@/components/fixture/EventsTimeline.vue'
import CenterTabs from '@/components/fixture/CenterTabs.vue'
import FormationTab from '@/components/fixture/tabs/FormationTab.vue'
import H2HTab from '@/components/fixture/tabs/H2HTab.vue'
import StatsTab from '@/components/fixture/tabs/StatsTab.vue'
import StandingsTab from '@/components/fixture/tabs/StandingsTab.vue'
import LineupsRight from '@/components/fixture/LineupsRight.vue'

const route = useRoute()
const router = useRouter()
const store = useFixtureDetailStore()
const {
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
} = storeToRefs(store)

const TAB_VALUES: ActiveTab[] = ['formation', 'h2h', 'stats', 'standings']

function tabFromQuery(): ActiveTab {
  const q = route.query.tab
  if (typeof q === 'string' && (TAB_VALUES as string[]).includes(q)) {
    return q as ActiveTab
  }
  return 'formation'
}

async function load(id: number) {
  await store.bootstrap(id, tabFromQuery())
  if (match.value.status === 'not_found') {
    void router.replace({ name: 'not-found' })
  }
}

onMounted(() => {
  load(Number(route.params.externalId))
})

watch(
  () => route.params.externalId,
  (next, prev) => {
    if (next !== prev && next != null) {
      load(Number(next))
    }
  },
)

async function onTabChange(tab: ActiveTab) {
  await store.setTab(tab)
  const query = { ...route.query }
  if (tab === 'formation') delete query.tab
  else query.tab = tab
  void router.replace({ query })
}

const showCancelled = computed(() =>
  match.value.value
    ? ['PST', 'CANC', 'SUSP'].includes(match.value.value.status_short)
    : false,
)
</script>

<template>
  <section
    class="fixture-detail-root"
    data-testid="fixture-detail-root"
    :data-league="leagueSlug ?? undefined"
    :data-league-id="leagueExternalId ?? undefined"
  >
    <template v-if="match.status === 'loading' || match.status === 'idle'">
      <div class="fixture-detail__loading" data-testid="fixture-detail-loading">
        불러오는 중…
      </div>
    </template>
    <template v-else-if="match.status === 'error'">
      <div class="fixture-detail__error" data-testid="fixture-detail-error">
        <p>매치 정보를 불러오지 못했습니다</p>
        <button type="button" @click="load(Number(route.params.externalId))">
          다시 시도
        </button>
      </div>
    </template>
    <template v-else-if="match.value">
      <MatchHeader :match="match.value" />
      <div v-if="!showCancelled" class="fixture-detail__three">
        <EventsTimeline
          :match="match.value"
          :slice="events"
          @retry="store.bootstrap(match.value!.external_id, activeTab)"
        />
        <CenterTabs :active="activeTab" @change="onTabChange">
          <FormationTab
            v-if="activeTab === 'formation'"
            :match="match.value"
            :slice="lineups"
          />
          <H2HTab
            v-else-if="activeTab === 'h2h'"
            :match="match.value"
            :slice="h2h"
          />
          <StatsTab
            v-else-if="activeTab === 'stats'"
            :match="match.value"
            :slice="statistics"
          />
          <StandingsTab
            v-else-if="activeTab === 'standings'"
            :match="match.value"
            :slice="standings"
          />
        </CenterTabs>
        <LineupsRight
          :match="match.value"
          :slice="lineups"
          :bench-expanded="benchExpanded"
          @toggle-bench="(t) => store.toggleBench(t)"
        />
      </div>
    </template>
  </section>
</template>

<style scoped>
.fixture-detail-root {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  overflow: hidden;
  background: var(--background, #fff);
}
.fixture-detail__three {
  display: grid;
  grid-template-columns: 25% 50% 25%;
  height: 75vh;
  overflow: hidden;
}
.fixture-detail__loading,
.fixture-detail__error {
  margin: auto;
  padding: 2rem;
  text-align: center;
  color: var(--muted-foreground);
}
</style>
