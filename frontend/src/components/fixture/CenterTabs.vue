<script setup lang="ts">
import type { ActiveTab } from '@/types/fixtureDetail'

const props = defineProps<{ active: ActiveTab }>()
const emit = defineEmits<{ (e: 'change', tab: ActiveTab): void }>()

const tabs: Array<{ id: ActiveTab; label: string }> = [
  { id: 'formation', label: '포메이션' },
  { id: 'h2h', label: 'H2H' },
  { id: 'stats', label: '경기 스탯' },
  { id: 'standings', label: '리그 랭킹' },
]

function pick(id: ActiveTab) {
  if (id === props.active) return
  emit('change', id)
}
</script>

<template>
  <div class="center-tabs" data-testid="center-tabs">
    <nav class="center-tabs__bar" role="tablist">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        role="tab"
        :aria-selected="active === t.id"
        :data-tab="t.id"
        :data-active="active === t.id ? 'true' : 'false'"
        class="center-tabs__btn"
        @click="pick(t.id)"
      >
        {{ t.label }}
      </button>
    </nav>
    <div class="center-tabs__body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.center-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-left: 1px solid var(--muted);
  border-right: 1px solid var(--muted);
  overflow: hidden;
}
.center-tabs__bar {
  display: flex;
  height: 40px;
  border-bottom: 1px solid var(--muted);
}
.center-tabs__btn {
  flex: 1;
  background: transparent;
  border: 0;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--muted-foreground);
  position: relative;
}
.center-tabs__btn[data-active='true'] {
  color: var(--theme-primary);
  font-weight: 600;
}
.center-tabs__btn[data-active='true']::after {
  content: '';
  position: absolute;
  left: 1rem;
  right: 1rem;
  bottom: 0;
  height: 2px;
  background: var(--theme-accent);
}
.center-tabs__body {
  flex: 1;
  overflow: hidden;
}
</style>
