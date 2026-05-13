<script setup lang="ts">
import { computed } from 'vue'
import type { TeamLineup } from '@/types/fixtureDetail'
import LineupRow from './LineupRow.vue'

const props = defineProps<{
  side: 'home' | 'away'
  lineup: TeamLineup | null
  isNs: boolean
  benchExpanded: boolean
}>()

const emit = defineEmits<{ (e: 'toggle-bench'): void }>()

const sideLabel = computed(() => (props.side === 'home' ? '홈' : '어웨이'))

const empty = computed(
  () =>
    !props.lineup ||
    !props.lineup.start_xi ||
    props.lineup.start_xi.length === 0,
)
</script>

<template>
  <section
    class="lineup-panel panel-scroll"
    :data-testid="`lineup-panel-${side}`"
  >
    <header class="lineup-panel__head">
      <strong
        >{{ sideLabel }} 라인업{{
          lineup?.formation ? ` · ${lineup.formation}` : ''
        }}</strong
      >
      <span v-if="lineup?.coach?.name" class="lineup-panel__coach">
        {{ lineup.coach.name }}
      </span>
    </header>

    <p
      v-if="isNs || empty"
      class="lineup-panel__placeholder"
      data-testid="lineup-empty"
    >
      라인업 미정 (kickoff 1시간 전 발표)
    </p>

    <div v-else class="lineup-panel__body">
      <ul class="lineup-panel__list">
        <li v-for="p in lineup!.start_xi" :key="p.player.external_id">
          <LineupRow :player="p" />
        </li>
      </ul>

      <button
        v-if="lineup!.bench.length"
        type="button"
        class="lineup-panel__bench-toggle"
        :aria-expanded="benchExpanded"
        :data-testid="`bench-toggle-${side}`"
        @click="emit('toggle-bench')"
      >
        벤치 {{ benchExpanded ? '▲' : '▼' }}
      </button>

      <ul
        v-if="benchExpanded"
        class="lineup-panel__list lineup-panel__list--bench"
        :data-testid="`bench-list-${side}`"
      >
        <li v-for="p in lineup!.bench" :key="p.player.external_id">
          <LineupRow :player="p" />
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.lineup-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
}
.lineup-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 0.5rem 0.75rem;
  font-size: 0.85rem;
  border-bottom: 1px solid var(--muted);
}
.lineup-panel__coach {
  color: var(--muted-foreground);
  font-size: 0.75rem;
}
.lineup-panel__placeholder {
  padding: 1rem;
  font-size: 0.85rem;
  color: var(--muted-foreground);
  text-align: center;
}
.lineup-panel__body {
  overflow-y: auto;
  scrollbar-width: none;
}
.lineup-panel__body::-webkit-scrollbar {
  display: none;
}
.lineup-panel__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.lineup-panel__bench-toggle {
  width: 100%;
  padding: 0.5rem;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--muted);
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--muted-foreground);
}
</style>
