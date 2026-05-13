<script setup lang="ts">
import { useHomeStore } from '@/stores/home'
import { slugFromId } from '@/lib/league-colors'
import type { Period } from '@/types/home'

const home = useHomeStore()

const leagueTabs: { id: number | null; label: string }[] = [
  { id: null, label: '전체' },
  { id: 39, label: 'EPL' },
  { id: 2, label: 'UCL' },
  { id: 3, label: 'UEL' },
  { id: 48, label: '카라바오' },
  { id: 45, label: 'FA' },
]

const periodToggles: { v: Period; label: string }[] = [
  { v: 'month', label: '월' },
  { v: 'week', label: '주' },
  { v: 'day', label: '일' },
]
</script>
<template>
  <div class="filters">
    <div class="filters__row" role="tablist" aria-label="리그 필터">
      <button
        v-for="t in leagueTabs"
        :key="t.label"
        type="button"
        role="tab"
        :aria-selected="home.fixtures.filter.league_id === t.id"
        :data-league="slugFromId(t.id ?? undefined) || undefined"
        :data-testid="'league-tab-' + (t.id ?? 'all')"
        :class="['tab', { 'tab--active': home.fixtures.filter.league_id === t.id }]"
        @click="home.setLeagueFilter(t.id)"
      >
        {{ t.label }}
      </button>
    </div>
    <div class="filters__row" role="tablist" aria-label="기간 필터">
      <button
        v-for="p in periodToggles"
        :key="p.v"
        type="button"
        role="tab"
        :aria-selected="home.fixtures.filter.period === p.v"
        :data-testid="'period-' + p.v"
        :class="['toggle', { 'toggle--active': home.fixtures.filter.period === p.v }]"
        @click="home.setPeriod(p.v)"
      >
        {{ p.label }}
      </button>
    </div>
  </div>
</template>
<style scoped>
.filters {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
}
.filters__row { display: flex; gap: 6px; flex-wrap: wrap; }
.tab,
.toggle {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
}
.tab--active {
  background: var(--theme-primary, var(--color-fg));
  color: var(--theme-on-primary, var(--color-bg));
  border-color: transparent;
}
.toggle--active {
  background: var(--color-fg);
  color: var(--color-bg);
}
</style>
