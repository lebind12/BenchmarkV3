<script setup lang="ts">
import type { TeamLineup, Slice, MatchDetail } from '@/types/fixtureDetail'
import FormationHalf from './FormationHalf.vue'

defineProps<{
  match: MatchDetail | null
  slice: Slice<{ home: TeamLineup; away: TeamLineup }>
}>()
</script>

<template>
  <section class="formation-tab" data-testid="tab-formation">
    <div v-if="slice.status === 'loading'" class="formation-tab__msg">
      불러오는 중…
    </div>
    <p
      v-else-if="
        match?.status_short === 'NS' ||
        !slice.value ||
        slice.value.home.start_xi.length === 0
      "
      class="formation-tab__msg"
      data-testid="formation-empty"
    >
      라인업 미정 (kickoff 1시간 전 발표)
    </p>
    <div v-else class="formation-tab__pitch">
      <FormationHalf :lineup="slice.value.home" side="home" />
      <FormationHalf :lineup="slice.value.away" side="away" />
    </div>
  </section>
</template>

<style scoped>
.formation-tab {
  height: 100%;
  display: flex;
}
.formation-tab__pitch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 100%;
  height: 100%;
}
.formation-tab__msg {
  margin: auto;
  font-size: 0.9rem;
  color: var(--muted-foreground);
}
</style>
