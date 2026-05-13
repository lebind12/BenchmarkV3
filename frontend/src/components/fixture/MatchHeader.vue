<script setup lang="ts">
import { computed } from 'vue'
import type { MatchDetail } from '@/types/fixtureDetail'
import GoalHistoryInline from './GoalHistoryInline.vue'

const props = defineProps<{ match: MatchDetail }>()

const isFinished = computed(() =>
  ['FT', 'AET', 'PEN'].includes(props.match.status_short),
)
const isLive = computed(() =>
  ['1H', 'HT', '2H', 'ET', 'BT', 'P'].includes(props.match.status_short),
)
const isCancelled = computed(() =>
  ['PST', 'CANC', 'SUSP'].includes(props.match.status_short),
)

const scoreLabel = computed(() => {
  const { status_short, goals_home, goals_away, penalty_home, penalty_away } =
    props.match
  if (status_short === 'NS') return 'vs'
  if (isCancelled.value) return '—'
  if (status_short === 'PEN' && penalty_home != null && penalty_away != null) {
    return `${goals_home}(${penalty_home}) - ${goals_away}(${penalty_away})`
  }
  return `${goals_home ?? 0} - ${goals_away ?? 0}`
})

const cancelLabel = computed(() => {
  if (props.match.status_short === 'PST') return '연기됨'
  if (props.match.status_short === 'CANC') return '취소됨'
  if (props.match.status_short === 'SUSP') return '중단됨'
  return null
})

function fmtKST(iso: string): string {
  const d = new Date(iso)
  // 'sv-SE' yields YYYY-MM-DD HH:MM:SS in local; use Asia/Seoul
  const parts = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(d)
  const get = (t: string) => parts.find((p) => p.type === t)?.value
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}`
}

const kickoffKst = computed(() => fmtKST(props.match.kickoff_at))
const kickoffTime = computed(() => kickoffKst.value.split(' ')[1])

const metaParts = computed(() => {
  const parts: string[] = []
  parts.push(
    props.match.league.name_ko ?? props.match.league.name,
  )
  if (props.match.round) parts.push(props.match.round)
  parts.push(props.match.status_short)
  if (props.match.venue?.name) parts.push(props.match.venue.name)
  if (props.match.referee) parts.push(props.match.referee)
  parts.push(`${kickoffKst.value} KST`)
  return parts
})

const homeName = computed(
  () => props.match.home.name_ko ?? props.match.home.name,
)
const awayName = computed(
  () => props.match.away.name_ko ?? props.match.away.name,
)
</script>

<template>
  <header class="match-header" data-testid="match-header">
    <div class="match-header__top">
      <div class="match-header__team match-header__team--home">
        <div class="match-header__logo" aria-hidden="true" />
        <div class="match-header__team-name">{{ homeName }}</div>
      </div>
      <div class="match-header__score" data-testid="match-score">
        <div class="match-header__score-value">{{ scoreLabel }}</div>
        <div v-if="match.status_short === 'NS'" class="match-header__kickoff">
          kickoff {{ kickoffTime }} KST
        </div>
        <div v-else-if="cancelLabel" class="match-header__status">
          {{ cancelLabel }}
        </div>
        <div v-else-if="isLive" class="match-header__status">
          {{ match.status_short }}
        </div>
      </div>
      <div class="match-header__team match-header__team--away">
        <div class="match-header__logo" aria-hidden="true" />
        <div class="match-header__team-name">{{ awayName }}</div>
      </div>
    </div>

    <div class="match-header__meta" data-testid="match-meta">
      <template v-for="(part, i) in metaParts" :key="i">
        <span>{{ part }}</span>
        <span v-if="i < metaParts.length - 1" class="match-header__dot">·</span>
      </template>
    </div>

    <GoalHistoryInline
      v-if="isFinished || isLive"
      :events="match.goal_events"
    />

    <p
      v-if="isCancelled"
      class="match-header__placeholder"
      data-testid="cancelled-placeholder"
    >
      경기가 진행되지 않았습니다
    </p>

    <p class="match-header__sla">이 페이지는 6시간마다 갱신됩니다</p>
  </header>
</template>

<style scoped>
.match-header {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 25vh;
  padding: 0.75rem 1rem;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--theme-primary) 8%, transparent),
    transparent
  );
  border-left: 4px solid var(--theme-primary);
  box-sizing: border-box;
}
.match-header__top {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 1rem;
}
.match-header__team {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.match-header__team--away {
  justify-content: flex-end;
}
.match-header__logo {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--muted);
}
.match-header__team-name {
  font-weight: 600;
  font-size: 1rem;
}
.match-header__score {
  text-align: center;
  min-width: 6rem;
}
.match-header__score-value {
  font-size: 2rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.match-header__kickoff,
.match-header__status {
  font-size: 0.75rem;
  color: var(--muted-foreground);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.match-header__meta {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--muted-foreground);
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
.match-header__dot {
  margin: 0 0.25rem;
}
.match-header__placeholder {
  margin-top: 0.25rem;
  font-size: 0.85rem;
  color: var(--muted-foreground);
}
.match-header__sla {
  margin: 0.25rem 0 0;
  font-size: 0.7rem;
  color: var(--muted-foreground);
  opacity: 0.7;
}
</style>
