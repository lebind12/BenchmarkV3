<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useHomeStore } from '@/stores/home'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'

const home = useHomeStore()
const router = useRouter()
function go() { router.push('/stats#injury') }
</script>
<template>
  <h3 class="face-title">부상</h3>
  <template v-if="home.injuries.status === 'loading'">
    <SkeletonCard v-for="i in 5" :key="i" />
  </template>
  <ErrorState v-else-if="home.injuries.status === 'error'" @retry="home.fetchInjuries()" />
  <EmptyState
    v-else-if="!home.injuries.value || home.injuries.value.length === 0"
    message="현재 보고된 부상자가 없습니다"
  />
  <template v-else>
    <button
      v-for="inj in home.injuries.value"
      :key="inj.id"
      type="button"
      class="inj-row"
      :data-testid="'injury-card-' + inj.id"
      @click="go"
    >
      <span class="inj-row__name">{{ inj.player.name_ko ?? inj.player.name }}</span>
      <span class="inj-row__type">{{ inj.injury_type }}</span>
      <span v-if="inj.expected_return" class="inj-row__date">~{{ inj.expected_return }}</span>
    </button>
  </template>
</template>
<style scoped>
.face-title { margin: 0 0 8px; font-size: 13px; color: var(--color-muted); }
.inj-row {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 6px 10px;
  margin-bottom: 4px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg);
  color: inherit;
  cursor: pointer;
  width: 100%;
  text-align: left;
}
.inj-row:hover { background: var(--color-card-hover); }
.inj-row__name { font-weight: 600; font-size: 13px; flex: 1; }
.inj-row__type { font-size: 11px; color: var(--color-muted); }
.inj-row__date { font-size: 10px; color: var(--color-muted); }
</style>
