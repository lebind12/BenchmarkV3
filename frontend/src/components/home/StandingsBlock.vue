<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useHomeStore } from '@/stores/home'
import PanelScroll from '@/components/common/PanelScroll.vue'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { slugFromId } from '@/lib/league-colors'

const home = useHomeStore()
const router = useRouter()

const leagues = [
  { id: 39, label: 'EPL' },
  { id: 2, label: 'UCL' },
  { id: 3, label: 'UEL' },
  { id: 48, label: '카라바오' },
  { id: 45, label: 'FA' },
]
const slug = computed(() => slugFromId(home.standings.league_id))

function go(slug: string) { router.push(`/teams/${slug}`) }
function onChange(e: Event) {
  const v = Number((e.target as HTMLSelectElement).value)
  home.setStandingsLeague(v)
}
const isCup = computed(() => home.standings.league_id === 48 || home.standings.league_id === 45)
</script>
<template>
  <section class="block" :data-league="slug" data-testid="standings-block">
    <div class="block__head">
      <strong>순위</strong>
      <select
        class="block__select"
        :value="home.standings.league_id"
        data-testid="standings-league-select"
        @change="onChange"
      >
        <option v-for="l in leagues" :key="l.id" :value="l.id">{{ l.label }}</option>
      </select>
    </div>
    <div class="block__body">
      <PanelScroll>
        <template v-if="home.standings.data.status === 'loading'">
          <SkeletonCard v-for="i in 8" :key="i" :height="32" />
        </template>
        <ErrorState v-else-if="home.standings.data.status === 'error'" @retry="home.fetchStandings()" />
        <EmptyState
          v-else-if="!home.standings.data.value || home.standings.data.value.length === 0"
          :message="isCup ? '이 대회는 토너먼트 형식이라 표 순위가 없습니다' : '현재 진행 중인 시즌 없음'"
        />
        <table v-else class="tbl">
          <thead><tr><th>#</th><th>팀</th><th>점</th><th>승무패</th></tr></thead>
          <tbody>
            <tr
              v-for="row in home.standings.data.value"
              :key="row.team.external_id"
              tabindex="0"
              :data-testid="'standings-row-' + row.team.slug"
              @click="go(row.team.slug)"
              @keydown.enter="go(row.team.slug)"
            >
              <td>{{ row.rank }}</td>
              <td>{{ row.team.short_name_ko ?? row.team.name_ko ?? row.team.name }}</td>
              <td>{{ row.points }}</td>
              <td>{{ row.win }}-{{ row.draw }}-{{ row.loss }}</td>
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
.block__select {
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
