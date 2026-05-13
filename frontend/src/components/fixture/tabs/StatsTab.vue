<script setup lang="ts">
import type { TeamStat, Slice, MatchDetail } from '@/types/fixtureDetail'
import StatBarRow from './StatBarRow.vue'

defineProps<{
  match: MatchDetail | null
  slice: Slice<{ home: TeamStat; away: TeamStat }>
}>()
</script>

<template>
  <section class="stats-tab" data-testid="tab-stats">
    <p
      v-if="match?.status_short === 'NS'"
      class="stats-tab__msg"
      data-testid="stats-empty-ns"
    >
      경기 시작 전 통계가 없습니다
    </p>
    <div v-else-if="slice.status === 'loading'" class="stats-tab__msg">
      불러오는 중…
    </div>
    <div v-else-if="slice.value" class="stats-tab__rows">
      <StatBarRow
        label="점유율"
        :home="slice.value.home.possession"
        :away="slice.value.away.possession"
        unit="%"
      />
      <StatBarRow
        label="슛 총"
        :home="slice.value.home.shots_total"
        :away="slice.value.away.shots_total"
      />
      <StatBarRow
        label="유효슛"
        :home="slice.value.home.shots_on_target"
        :away="slice.value.away.shots_on_target"
      />
      <StatBarRow
        label="패스"
        :home="slice.value.home.passes_total"
        :away="slice.value.away.passes_total"
      />
      <StatBarRow
        label="패스 정확도"
        :home="slice.value.home.passes_accuracy"
        :away="slice.value.away.passes_accuracy"
        unit="%"
      />
      <StatBarRow
        label="코너킥"
        :home="slice.value.home.corners"
        :away="slice.value.away.corners"
      />
      <StatBarRow
        label="파울"
        :home="slice.value.home.fouls"
        :away="slice.value.away.fouls"
      />
      <StatBarRow
        label="옐로"
        :home="slice.value.home.yellow"
        :away="slice.value.away.yellow"
      />
      <StatBarRow
        label="레드"
        :home="slice.value.home.red"
        :away="slice.value.away.red"
      />
      <StatBarRow
        label="오프사이드"
        :home="slice.value.home.offsides"
        :away="slice.value.away.offsides"
      />
    </div>
    <p v-else class="stats-tab__msg">데이터 없음</p>
  </section>
</template>

<style scoped>
.stats-tab {
  height: 100%;
  overflow-y: auto;
  scrollbar-width: none;
}
.stats-tab::-webkit-scrollbar {
  display: none;
}
.stats-tab__rows {
  display: flex;
  flex-direction: column;
  padding: 0.25rem 0;
}
.stats-tab__msg {
  margin: auto;
  padding: 1rem;
  font-size: 0.9rem;
  color: var(--muted-foreground);
  text-align: center;
}
</style>
