<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useHomeStore } from '@/stores/home'
import FixtureFilters from './FixtureFilters.vue'
import FixtureCard from './FixtureCard.vue'
import PanelScroll from '@/components/common/PanelScroll.vue'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'

const home = useHomeStore()
const router = useRouter()

function openFixture(id: number) {
  router.push(`/fixtures/${id}`)
}
function goFixturesPage() {
  router.push('/fixtures')
}
</script>
<template>
  <section class="center" data-testid="center-panel">
    <FixtureFilters />
    <div class="center__list">
      <PanelScroll>
        <template v-if="home.fixtures.data.status === 'loading'">
          <SkeletonCard v-for="i in 8" :key="i" :height="72" />
        </template>
        <ErrorState
          v-else-if="home.fixtures.data.status === 'error'"
          @retry="home.fetchFixtures()"
        />
        <template v-else-if="!home.fixtures.data.value || home.fixtures.data.value.length === 0">
          <EmptyState
            message="선택한 조건에 경기가 없습니다"
            action-label="다음 경기일정 보기"
            data-testid="fixtures-empty"
            @action="goFixturesPage"
          />
          <div class="reset-row">
            <button type="button" class="reset" data-testid="fixtures-reset" @click="home.resetFixtureFilters()">
              기본값으로 초기화
            </button>
          </div>
        </template>
        <template v-else>
          <FixtureCard
            v-for="fx in home.fixtures.data.value"
            :key="fx.external_id"
            :fixture="fx"
            @open="openFixture"
          />
        </template>
      </PanelScroll>
    </div>
  </section>
</template>
<style scoped>
.center { display: flex; flex-direction: column; height: 100%; }
.center__list { flex: 1; min-height: 0; padding: 8px 12px 0; }
.reset-row { text-align: center; padding-top: 8px; }
.reset {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}
</style>
