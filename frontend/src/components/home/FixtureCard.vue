<script setup lang="ts">
import type { FixtureSummary } from '@/types/home'
import { kstTime } from '@/lib/format/datetime'
import { LEAGUE_SHORT_KO } from '@/lib/league-colors'

const props = defineProps<{ fixture: FixtureSummary }>()
defineEmits<{ (e: 'open', id: number): void }>()

function leagueShort(): string {
  return props.fixture.league.short_name_ko ?? LEAGUE_SHORT_KO[props.fixture.league.slug] ?? props.fixture.league.name
}
function teamName(t: FixtureSummary['home']): string {
  return t.name_ko ?? t.name
}
function centerLabel(fx: FixtureSummary): string {
  if (fx.status_short === 'NS' || fx.status_short === 'PST') return kstTime(fx.kickoff_at)
  if (fx.goals_home != null && fx.goals_away != null) return `${fx.goals_home} - ${fx.goals_away}`
  return kstTime(fx.kickoff_at)
}
</script>
<template>
  <button
    type="button"
    class="fx"
    :data-league="fixture.league.slug"
    :data-testid="'fixture-card-' + fixture.external_id"
    @click="$emit('open', fixture.external_id)"
  >
    <span class="fx__badge" :data-testid="'fixture-badge-' + fixture.external_id">{{ leagueShort() }}</span>
    <span class="fx__team fx__home">{{ teamName(fixture.home) }}</span>
    <span class="fx__center">{{ centerLabel(fixture) }}</span>
    <span class="fx__team fx__away">{{ teamName(fixture.away) }}</span>
    <span class="fx__status">{{ fixture.status_short }}</span>
  </button>
</template>
<style scoped>
.fx {
  display: grid;
  grid-template-columns: 64px 1fr 80px 1fr 48px;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--theme-primary, var(--color-border));
  border-radius: 8px;
  cursor: pointer;
  color: inherit;
  text-align: left;
}
.fx:hover { background: var(--color-card-hover); }
.fx__badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  background: var(--theme-primary, var(--color-muted));
  color: var(--theme-on-primary, #fff);
}
.fx__team { font-size: 13px; font-weight: 500; }
.fx__home { text-align: right; }
.fx__away { text-align: left; }
.fx__center { text-align: center; font-weight: 700; font-size: 14px; }
.fx__status {
  font-size: 11px;
  color: var(--color-muted);
  text-align: right;
}
</style>
