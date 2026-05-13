<script setup lang="ts">
import { computed } from 'vue'
import type { TimelineEvent, Slice, MatchDetail } from '@/types/fixtureDetail'

const props = defineProps<{
  match: MatchDetail | null
  slice: Slice<TimelineEvent[]>
}>()

const emit = defineEmits<{ (e: 'retry'): void }>()

const sorted = computed(() => {
  const list = props.slice.value ?? []
  return [...list].sort((a, b) => {
    if (a.minute !== b.minute) return a.minute - b.minute
    return (a.extra ?? 0) - (b.extra ?? 0)
  })
})

function iconFor(type: TimelineEvent['type']): string {
  switch (type) {
    case 'goal':
      return '⚽'
    case 'goal_penalty':
      return '⚽(P)'
    case 'goal_own':
      return '⚽(OG)'
    case 'yellow_card':
      return '🟨'
    case 'red_card':
      return '🟥'
    case 'yellow_red':
      return '🟨→🟥'
    case 'substitution':
      return '🔄'
    case 'var':
      return '🎬'
  }
}

function tooltip(e: TimelineEvent): string {
  const name = e.player.name_ko ?? e.player.name
  const min = e.extra ? `${e.minute}+${e.extra}'` : `${e.minute}'`
  switch (e.type) {
    case 'goal': {
      const a = e.assist ? ` (${e.assist.name_ko ?? e.assist.name} 어시)` : ''
      return `${min} — ${name} ⚽${a}`
    }
    case 'goal_penalty':
      return `${min} — ${name} 페널티골`
    case 'goal_own':
      return `${min} — ${name} 자책골`
    case 'yellow_card':
      return `${min} — ${name} 경고${e.detail ? ` (${e.detail})` : ''}`
    case 'red_card':
      return `${min} — ${name} 퇴장`
    case 'yellow_red':
      return `${min} — ${name} 경고 누적 퇴장`
    case 'substitution': {
      const out = e.player_out
        ? `${e.player_out.name_ko ?? e.player_out.name}`
        : '?'
      return `${min} — IN ${name} / OUT ${out}`
    }
    case 'var':
      return `${min} — VAR${e.detail ? ` (${e.detail})` : ''}`
  }
}

const homeId = computed(() => props.match?.home.external_id ?? null)
const awayId = computed(() => props.match?.away.external_id ?? null)

const isNs = computed(() => props.match?.status_short === 'NS')
</script>

<template>
  <section
    class="events-timeline panel-scroll"
    role="region"
    aria-label="경기 이벤트 타임라인"
    data-testid="events-timeline"
  >
    <header class="events-timeline__head">
      <div aria-label="홈 이벤트">홈</div>
      <div aria-label="어웨이 이벤트">어웨이</div>
    </header>

    <div v-if="slice.status === 'loading'" class="events-timeline__msg">
      불러오는 중…
    </div>
    <div
      v-else-if="slice.status === 'error'"
      class="events-timeline__msg events-timeline__msg--error"
      data-testid="events-error"
    >
      이벤트를 불러오지 못했습니다
      <button type="button" @click="emit('retry')">다시 시도</button>
    </div>
    <div
      v-else-if="!sorted.length && isNs"
      class="events-timeline__msg"
      data-testid="events-empty-ns"
    >
      <span aria-hidden="true">🕒</span> 경기 시작 전입니다
    </div>
    <div
      v-else-if="!sorted.length"
      class="events-timeline__msg"
      data-testid="events-empty-ft"
    >
      경기 이벤트 정보가 없습니다
    </div>
    <ol v-else class="events-timeline__rows">
      <li
        v-for="e in sorted"
        :key="e.id"
        class="events-timeline__row"
        :data-team="e.team_external_id === homeId ? 'home' : 'away'"
      >
        <div class="events-timeline__cell" :data-side="'home'">
          <button
            v-if="e.team_external_id === homeId"
            type="button"
            class="events-timeline__icon"
            :data-event-type="e.type"
            :title="tooltip(e)"
            :aria-label="tooltip(e)"
          >
            {{ iconFor(e.type) }} {{ e.extra ? `${e.minute}+${e.extra}'` : `${e.minute}'` }}
          </button>
        </div>
        <div class="events-timeline__cell" :data-side="'away'">
          <button
            v-if="e.team_external_id === awayId"
            type="button"
            class="events-timeline__icon"
            :data-event-type="e.type"
            :title="tooltip(e)"
            :aria-label="tooltip(e)"
          >
            {{ iconFor(e.type) }} {{ e.extra ? `${e.minute}+${e.extra}'` : `${e.minute}'` }}
          </button>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.events-timeline {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.events-timeline__head {
  display: grid;
  grid-template-columns: 1fr 1fr;
  font-size: 0.75rem;
  color: var(--muted-foreground);
  padding: 0.5rem 0.5rem 0.25rem;
  border-bottom: 1px solid var(--muted);
}
.events-timeline__rows {
  list-style: none;
  margin: 0;
  padding: 0.25rem 0.5rem;
  overflow-y: auto;
  scrollbar-width: none;
}
.events-timeline__rows::-webkit-scrollbar {
  display: none;
}
.events-timeline__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 0.15rem 0;
}
.events-timeline__icon {
  font-size: 0.8rem;
  background: transparent;
  border: 0;
  cursor: pointer;
  color: var(--theme-primary);
  padding: 0.1rem 0.3rem;
}
.events-timeline__msg {
  padding: 1rem;
  font-size: 0.85rem;
  color: var(--muted-foreground);
  text-align: center;
}
.events-timeline__msg--error button {
  margin-left: 0.5rem;
}
</style>
