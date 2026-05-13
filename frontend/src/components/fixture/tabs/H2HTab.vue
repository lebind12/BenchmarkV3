<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type {
  H2HFixture,
  Slice,
  MatchDetail,
} from '@/types/fixtureDetail'

const props = defineProps<{
  match: MatchDetail | null
  slice: Slice<H2HFixture[]>
}>()

const router = useRouter()

function fmtDate(iso: string) {
  return iso.slice(0, 10)
}

function resultBadge(h: H2HFixture): 'W' | 'D' | 'L' | null {
  if (!props.match) return null
  const homeId = props.match.home.external_id
  const wasHome = h.home.external_id === homeId
  const ours = wasHome ? h.goals_home : h.goals_away
  const theirs = wasHome ? h.goals_away : h.goals_home
  if (ours > theirs) return 'W'
  if (ours < theirs) return 'L'
  return 'D'
}

function go(id: number) {
  void router.push(`/fixtures/${id}`)
}

const list = computed(() => props.slice.value ?? [])
</script>

<template>
  <section class="h2h-tab" data-testid="tab-h2h">
    <div v-if="slice.status === 'loading'" class="h2h-tab__msg">
      불러오는 중…
    </div>
    <p
      v-else-if="!list.length"
      class="h2h-tab__msg"
      data-testid="h2h-empty"
    >
      두 팀 간 최근 5경기 기록이 없습니다
    </p>
    <ul v-else class="h2h-tab__list">
      <li v-for="h in list" :key="h.external_id">
        <button
          type="button"
          class="h2h-tab__row"
          data-testid="h2h-row"
          @click="go(h.external_id)"
        >
          <span class="h2h-tab__date">{{ fmtDate(h.kickoff_at) }}</span>
          <span class="h2h-tab__league">{{ h.league.short_name_ko ?? h.league.name }}</span>
          <span class="h2h-tab__teams">
            {{ h.home.name_ko ?? h.home.name }}
            {{ h.goals_home }} - {{ h.goals_away }}
            {{ h.away.name_ko ?? h.away.name }}
          </span>
          <span
            class="h2h-tab__badge"
            :data-result="resultBadge(h)"
            v-if="resultBadge(h)"
          >
            {{ resultBadge(h) }}
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.h2h-tab {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.h2h-tab__list {
  list-style: none;
  margin: 0;
  padding: 0.25rem 0;
  overflow-y: auto;
  scrollbar-width: none;
}
.h2h-tab__list::-webkit-scrollbar {
  display: none;
}
.h2h-tab__row {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  gap: 0.5rem;
  align-items: center;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--muted);
  cursor: pointer;
  font-size: 0.85rem;
}
.h2h-tab__date,
.h2h-tab__league {
  color: var(--muted-foreground);
  font-size: 0.75rem;
}
.h2h-tab__badge {
  font-weight: 700;
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  color: #fff;
}
.h2h-tab__badge[data-result='W'] {
  background: #16a34a;
}
.h2h-tab__badge[data-result='D'] {
  background: #6b7280;
}
.h2h-tab__badge[data-result='L'] {
  background: #dc2626;
}
.h2h-tab__msg {
  margin: auto;
  font-size: 0.9rem;
  color: var(--muted-foreground);
  text-align: center;
}
</style>
