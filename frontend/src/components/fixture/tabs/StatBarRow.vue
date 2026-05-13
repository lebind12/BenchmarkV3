<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  home: number | null
  away: number | null
  unit?: string
}>()

const total = computed(() => {
  const h = props.home ?? 0
  const a = props.away ?? 0
  return h + a || 1
})

const homePct = computed(() =>
  props.home != null ? Math.round((props.home / total.value) * 100) : 0,
)
const awayPct = computed(() =>
  props.away != null ? Math.round((props.away / total.value) * 100) : 0,
)

const homeText = computed(() =>
  props.home == null ? '—' : `${props.home}${props.unit ?? ''}`,
)
const awayText = computed(() =>
  props.away == null ? '—' : `${props.away}${props.unit ?? ''}`,
)
</script>

<template>
  <div class="stat-bar-row" data-testid="stat-bar-row">
    <div class="stat-bar-row__home-val">{{ homeText }}</div>
    <div class="stat-bar-row__label">{{ label }}</div>
    <div class="stat-bar-row__away-val">{{ awayText }}</div>
    <div class="stat-bar-row__bars">
      <span
        class="stat-bar-row__bar stat-bar-row__bar--home"
        :style="{ width: homePct + '%' }"
        data-testid="stat-bar-home"
      />
      <span
        class="stat-bar-row__bar stat-bar-row__bar--away"
        :style="{ width: awayPct + '%' }"
        data-testid="stat-bar-away"
      />
    </div>
  </div>
</template>

<style scoped>
.stat-bar-row {
  display: grid;
  grid-template-columns: 3rem 1fr 3rem;
  grid-template-rows: auto 0.4rem;
  column-gap: 0.5rem;
  align-items: center;
  padding: 0.4rem 0.5rem;
  font-size: 0.8rem;
}
.stat-bar-row__home-val {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.stat-bar-row__away-val {
  text-align: left;
  font-variant-numeric: tabular-nums;
}
.stat-bar-row__label {
  text-align: center;
  color: var(--muted-foreground);
}
.stat-bar-row__bars {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  height: 0.35rem;
  gap: 0.25rem;
}
.stat-bar-row__bar--home {
  background: color-mix(in srgb, var(--theme-primary) 60%, transparent);
  justify-self: end;
  height: 100%;
  border-radius: 2px;
}
.stat-bar-row__bar--away {
  background: color-mix(in srgb, var(--theme-secondary) 60%, transparent);
  justify-self: start;
  height: 100%;
  border-radius: 2px;
}
</style>
