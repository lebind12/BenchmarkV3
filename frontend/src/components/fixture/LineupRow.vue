<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { LineupPlayer } from '@/types/fixtureDetail'

const props = defineProps<{ player: LineupPlayer }>()

const router = useRouter()

const displayName =
  props.player.player.name_ko ?? props.player.player.name

function go() {
  void router.push(`/players/${props.player.player.slug}`)
}
</script>

<template>
  <button
    type="button"
    class="lineup-row"
    data-testid="lineup-row"
    @click="go"
  >
    <span class="lineup-row__num">{{ player.number }}</span>
    <span class="lineup-row__pos">{{ player.position }}</span>
    <span class="lineup-row__name">{{ displayName }}</span>
    <span
      v-if="player.rating != null"
      class="lineup-row__rating"
      data-testid="lineup-rating"
    >
      {{ player.rating.toFixed(1) }}
    </span>
  </button>
</template>

<style scoped>
.lineup-row {
  display: grid;
  grid-template-columns: 2rem 2.5rem 1fr auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.5rem;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid color-mix(in srgb, var(--muted) 60%, transparent);
  cursor: pointer;
  font-size: 0.85rem;
}
.lineup-row__num {
  font-weight: 600;
  color: var(--theme-primary);
}
.lineup-row__pos {
  font-size: 0.7rem;
  color: var(--muted-foreground);
  text-transform: uppercase;
}
.lineup-row__name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lineup-row__rating {
  font-variant-numeric: tabular-nums;
  font-size: 0.8rem;
  color: var(--theme-primary);
}
</style>
