<script setup lang="ts">
import type { GoalEventSummary } from '@/types/fixtureDetail'

defineProps<{
  events: GoalEventSummary[]
}>()

function suffix(t: GoalEventSummary['type']) {
  if (t === 'penalty') return ' (PEN)'
  if (t === 'own_goal') return ' (OG)'
  return ''
}

function minuteLabel(e: GoalEventSummary) {
  return e.extra ? `${e.minute}+${e.extra}'` : `${e.minute}'`
}

function displayName(e: GoalEventSummary) {
  return e.scorer.name_ko ?? e.scorer.name
}
</script>

<template>
  <div v-if="events.length" class="goal-history" data-testid="goal-history">
    <span
      v-for="(e, i) in events"
      :key="`${e.minute}-${e.scorer.external_id}-${i}`"
      class="goal-history__item"
    >
      <span class="goal-history__icon" aria-hidden="true">⚽</span>
      <span>{{ displayName(e) }} {{ minuteLabel(e) }}{{ suffix(e.type) }}</span>
      <span v-if="i < events.length - 1" class="goal-history__sep">/</span>
    </span>
  </div>
</template>

<style scoped>
.goal-history {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 0.75rem;
  font-size: clamp(11px, 0.85vw, 14px);
  overflow: hidden;
}
.goal-history__item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  white-space: nowrap;
}
.goal-history__icon {
  color: var(--theme-primary);
}
.goal-history__sep {
  color: var(--muted-foreground);
  margin-left: 0.5rem;
}
</style>
