<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useHomeStore } from '@/stores/home'
import PanelScroll from '@/components/common/PanelScroll.vue'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { slugFromId } from '@/lib/league-colors'
import type { MetricKey } from '@/types/home'

const home = useHomeStore()
const router = useRouter()

const leagues = [
  { id: 39, label: 'EPL' },
  { id: 2, label: 'UCL' },
  { id: 3, label: 'UEL' },
  { id: 48, label: '카라바오' },
  { id: 45, label: 'FA' },
]
const metrics: { v: MetricKey; label: string }[] = [
  { v: 'goals', label: '득점' },
  { v: 'assists', label: '도움' },
  { v: 'yellow_cards', label: '경고' },
  { v: 'red_cards', label: '퇴장' },
]
const slug = computed(() => slugFromId(home.topPlayers.league_id))

function go(slug: string) { router.push(`/players/${slug}`) }
function onMetric(e: Event) {
  home.setTopPlayersMetric((e.target as HTMLSelectElement).value as MetricKey)
}
function onLeague(e: Event) {
  home.setTopPlayersLeague(Number((e.target as HTMLSelectElement).value))
}
</script>
<template>
  <section class="block" :data-league="slug" data-testid="top-players-block">
    <div class="block__head">
      <strong>스탯</strong>
      <div class="block__controls">
        <select
          :value="home.topPlayers.metric"
          data-testid="topp-metric-select"
          @change="onMetric"
        >
          <option v-for="m in metrics" :key="m.v" :value="m.v">{{ m.label }}</option>
        </select>
        <select
          :value="home.topPlayers.league_id"
          data-testid="topp-league-select"
          @change="onLeague"
        >
          <option v-for="l in leagues" :key="l.id" :value="l.id">{{ l.label }}</option>
        </select>
      </div>
    </div>
    <div class="block__body">
      <PanelScroll>
        <template v-if="home.topPlayers.data.status === 'loading'">
          <SkeletonCard v-for="i in 8" :key="i" :height="32" />
        </template>
        <ErrorState v-else-if="home.topPlayers.data.status === 'error'" @retry="home.fetchTopPlayers()" />
        <EmptyState
          v-else-if="!home.topPlayers.data.value || home.topPlayers.data.value.length === 0"
          message="해당 조건의 스탯이 없습니다"
        />
        <table v-else class="tbl">
          <thead><tr><th>#</th><th>선수</th><th>수치</th></tr></thead>
          <tbody>
            <tr
              v-for="row in home.topPlayers.data.value"
              :key="row.player.external_id"
              tabindex="0"
              :data-testid="'topp-row-' + row.player.slug"
              @click="go(row.player.slug)"
              @keydown.enter="go(row.player.slug)"
            >
              <td>{{ row.rank }}</td>
              <td>{{ row.player.name_ko ?? row.player.name }}</td>
              <td>{{ row.metric_value }}</td>
            </tr>
          </tbody>
        </table>
      </PanelScroll>
    </div>
  </section>
</template>
<style scoped>
.block { display: flex; flex-direction: column; height: 100%; }
.block__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border);
  background: var(--theme-primary, transparent);
  color: var(--theme-on-primary, var(--color-fg));
}
.block__controls { display: flex; gap: 4px; }
.block__head select {
  background: var(--color-bg);
  color: var(--color-fg);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 2px 6px;
}
.block__body { flex: 1; min-height: 0; padding: 4px 8px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 12px; }
.tbl th { text-align: left; color: var(--color-muted); font-weight: 500; padding: 4px 6px; position: sticky; top: 0; background: var(--color-bg); }
.tbl td { padding: 4px 6px; border-top: 1px solid var(--color-border); cursor: pointer; }
.tbl tr:hover td { background: var(--color-card-hover); }
</style>
