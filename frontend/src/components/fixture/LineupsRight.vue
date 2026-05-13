<script setup lang="ts">
import type { TeamLineup, Slice, MatchDetail } from '@/types/fixtureDetail'
import LineupPanel from './LineupPanel.vue'

defineProps<{
  match: MatchDetail | null
  slice: Slice<{ home: TeamLineup; away: TeamLineup }>
  benchExpanded: { home: boolean; away: boolean }
}>()

const emit = defineEmits<{ (e: 'toggle-bench', team: 'home' | 'away'): void }>()
</script>

<template>
  <aside class="lineups-right" data-testid="lineups-right">
    <LineupPanel
      side="home"
      :lineup="slice.value?.home ?? null"
      :is-ns="match?.status_short === 'NS'"
      :bench-expanded="benchExpanded.home"
      @toggle-bench="emit('toggle-bench', 'home')"
    />
    <LineupPanel
      side="away"
      :lineup="slice.value?.away ?? null"
      :is-ns="match?.status_short === 'NS'"
      :bench-expanded="benchExpanded.away"
      @toggle-bench="emit('toggle-bench', 'away')"
    />
  </aside>
</template>

<style scoped>
.lineups-right {
  display: grid;
  grid-template-rows: 50% 50%;
  height: 100%;
  overflow: hidden;
  border-left: 1px solid var(--muted);
}
.lineups-right > :first-child {
  border-bottom: 1px solid var(--muted);
}
</style>
