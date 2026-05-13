<script setup lang="ts">
import { useHomeStore } from '@/stores/home'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import { relativeFromNow } from '@/lib/format/datetime'

const home = useHomeStore()
</script>
<template>
  <h3 class="face-title">뉴스</h3>
  <template v-if="home.news.status === 'loading'">
    <SkeletonCard v-for="i in 5" :key="i" />
  </template>
  <ErrorState v-else-if="home.news.status === 'error'" @retry="home.fetchNews()" />
  <EmptyState
    v-else-if="!home.news.value || home.news.value.length === 0"
    message="오늘 EPL 관련 뉴스가 없습니다"
  />
  <template v-else>
    <a
      v-for="n in home.news.value"
      :key="n.id"
      :href="n.url"
      target="_blank"
      rel="noopener noreferrer"
      class="news-card"
      :data-testid="'news-card-' + n.id"
    >
      <div class="news-card__title">{{ n.title_ko ?? n.title }}</div>
      <div class="news-card__meta">
        <span>{{ n.source }}</span>
        <span aria-hidden="true">·</span>
        <span>{{ relativeFromNow(n.published_at) }}</span>
      </div>
    </a>
    <p class="refresh-note">이 정보는 6시간마다 갱신됩니다</p>
  </template>
</template>
<style scoped>
.face-title { margin: 0 0 8px; font-size: 13px; color: var(--color-muted); }
.news-card {
  display: block;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  margin-bottom: 6px;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}
.news-card:hover { background: var(--color-card-hover); }
.news-card__title {
  font-size: 13px;
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.news-card__meta { font-size: 11px; color: var(--color-muted); display: flex; gap: 4px; }
.refresh-note { font-size: 10px; color: var(--color-muted); text-align: center; margin: 4px 0 0; }
</style>
