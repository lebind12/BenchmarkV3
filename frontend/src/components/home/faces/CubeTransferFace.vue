<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useHomeStore } from '@/stores/home'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'

const home = useHomeStore()
const router = useRouter()
function go() { router.push('/stats#transfer') }
</script>
<template>
  <h3 class="face-title">이적</h3>
  <template v-if="home.transfers.status === 'loading'">
    <SkeletonCard v-for="i in 5" :key="i" />
  </template>
  <ErrorState v-else-if="home.transfers.status === 'error'" @retry="home.fetchTransfers()" />
  <EmptyState
    v-else-if="!home.transfers.value || home.transfers.value.length === 0"
    message="최근 이적 정보가 없습니다"
  />
  <template v-else>
    <button
      v-for="t in home.transfers.value"
      :key="t.id"
      type="button"
      class="tr-row"
      :data-testid="'transfer-card-' + t.id"
      @click="go"
    >
      <span class="tr-row__name">{{ t.player.name_ko ?? t.player.name }}</span>
      <span class="tr-row__path">
        {{ t.from_team.name_ko ?? t.from_team.name }} → {{ t.to_team.name_ko ?? t.to_team.name }}
      </span>
      <span class="tr-row__date">{{ t.transfer_date }}</span>
    </button>
  </template>
</template>
<style scoped>
.face-title { margin: 0 0 8px; font-size: 13px; color: var(--color-muted); }
.tr-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
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
.tr-row:hover { background: var(--color-card-hover); }
.tr-row__name { font-weight: 600; font-size: 13px; }
.tr-row__path { font-size: 11px; color: var(--color-muted); }
.tr-row__date { font-size: 10px; color: var(--color-muted); }
</style>
