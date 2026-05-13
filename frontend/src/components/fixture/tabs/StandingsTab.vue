<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type {
  LeagueStandingsPayload,
  Slice,
  MatchDetail,
} from '@/types/fixtureDetail'

const props = defineProps<{
  match: MatchDetail | null
  slice: Slice<LeagueStandingsPayload>
}>()

const router = useRouter()

// Cup leagues (Carabao 48, FA 45) have no standings even when fetched ok.
const isCupNoStandings = computed(() => {
  const id = props.match?.league.external_id
  return id === 48 || id === 45
})

const isUclTournament = computed(
  () =>
    props.match?.league.external_id === 2 &&
    props.slice.value?.group_name == null &&
    (props.slice.value?.rows.length ?? 0) === 0,
)

const rows = computed(() => props.slice.value?.rows ?? [])
const highlighted = computed(
  () => new Set(props.slice.value?.highlighted_team_ids ?? []),
)
const homeId = computed(() => props.match?.home.external_id ?? null)

function go(slug: string) {
  void router.push(`/teams/${slug}`)
}
</script>

<template>
  <section class="standings-tab" data-testid="tab-standings">
    <p
      v-if="isCupNoStandings || isUclTournament"
      class="standings-tab__msg"
      data-testid="standings-tournament"
    >
      토너먼트 스테이지: 그룹 순위가 없습니다
    </p>
    <table v-else-if="rows.length" class="standings-tab__table">
      <thead>
        <tr>
          <th>#</th>
          <th>팀</th>
          <th>경기</th>
          <th>승-무-패</th>
          <th>득실</th>
          <th>승점</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in rows"
          :key="r.team.external_id"
          :data-highlighted="highlighted.has(r.team.external_id) ? 'true' : 'false'"
          :data-side="r.team.external_id === homeId ? 'home' : 'away'"
          data-testid="standings-row"
          @click="go(r.team.slug)"
        >
          <td>{{ r.rank }}</td>
          <td>{{ r.team.name_ko ?? r.team.name }}</td>
          <td>{{ r.played }}</td>
          <td>{{ r.win }}-{{ r.draw }}-{{ r.loss }}</td>
          <td>{{ r.goal_diff > 0 ? '+' : '' }}{{ r.goal_diff }}</td>
          <td>{{ r.points }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="standings-tab__msg">불러오는 중…</p>
  </section>
</template>

<style scoped>
.standings-tab {
  height: 100%;
  overflow-y: auto;
  scrollbar-width: none;
}
.standings-tab::-webkit-scrollbar {
  display: none;
}
.standings-tab__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.standings-tab__table th,
.standings-tab__table td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid var(--muted);
  text-align: left;
}
.standings-tab__table tbody tr {
  cursor: pointer;
}
.standings-tab__table tbody tr[data-highlighted='true'] {
  background: color-mix(in srgb, var(--theme-primary) 10%, transparent);
  border-left: 4px solid var(--theme-primary);
}
.standings-tab__table tbody tr[data-highlighted='true'][data-side='away'] {
  border-left-color: var(--theme-secondary);
}
.standings-tab__msg {
  padding: 1rem;
  font-size: 0.9rem;
  color: var(--muted-foreground);
  text-align: center;
}
</style>
