<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useHomeStore } from '@/stores/home'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'

const home = useHomeStore()
const router = useRouter()
function go(slug: string) { router.push(`/players/${slug}`) }
</script>
<template>
  <h3 class="face-title">핫 선수</h3>
  <template v-if="home.hot.status === 'loading'">
    <SkeletonCard v-for="i in 5" :key="i" />
  </template>
  <ErrorState v-else-if="home.hot.status === 'error'" @retry="home.fetchHot()" />
  <EmptyState
    v-else-if="!home.hot.value || home.hot.value.length === 0"
    message="시즌 휴식 중입니다"
  />
  <template v-else>
    <button
      v-for="h in home.hot.value"
      :key="h.player.external_id"
      type="button"
      class="hot-row"
      :data-testid="'hot-card-' + h.player.slug"
      @click="go(h.player.slug)"
    >
      <span class="hot-row__name">{{ h.player.name_ko ?? h.player.name }}</span>
      <span class="hot-row__team">{{ h.player.team.name_ko ?? h.player.team.name }}</span>
      <span class="hot-row__score">{{ h.score }}</span>
    </button>
  </template>
</template>
<style scoped>
.face-title { margin: 0 0 8px; font-size: 13px; color: var(--color-muted); }
.hot-row {
  display: flex;
  align-items: center;
  gap: 8px;
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
.hot-row:hover { background: var(--color-card-hover); }
.hot-row__name { font-weight: 600; font-size: 13px; flex: 1; }
.hot-row__team { font-size: 11px; color: var(--color-muted); }
.hot-row__score { font-weight: 700; font-size: 13px; }
</style>
