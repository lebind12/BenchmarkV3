<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const tabs = computed(() => {
  const base = [
    { path: '/', label: '홈' },
    { path: '/fixtures', label: '경기' },
    { path: '/standings', label: '순위' },
    { path: '/teams', label: '팀' },
    { path: '/players', label: '선수' },
    { path: '/stats', label: '스탯' },
  ]
  if (auth.isStreamer) base.push({ path: '/broadcast', label: '방송' })
  return base
})

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark')
  localStorage.setItem('theme', isDark ? 'dark' : 'light')
}
</script>
<template>
  <header class="hdr" role="banner">
    <div class="hdr__logo">⚽ 벤치마크</div>
    <nav class="hdr__nav" aria-label="주요 메뉴">
      <router-link
        v-for="t in tabs"
        :key="t.path"
        :to="t.path"
        class="hdr__tab"
        active-class="hdr__tab--active"
        :data-testid="`nav-${t.label}`"
      >
        {{ t.label }}
      </router-link>
    </nav>
    <div class="hdr__right">
      <button
        type="button"
        class="hdr__icon"
        aria-label="테마 토글"
        data-testid="theme-toggle"
        @click="toggleTheme"
      >
        ☾
      </button>
      <button
        v-if="!auth.isLoggedIn"
        type="button"
        class="hdr__login"
        data-testid="auth-login"
      >
        로그인
      </button>
      <button v-else type="button" class="hdr__login" data-testid="auth-profile">
        프로필
      </button>
    </div>
  </header>
</template>
<style scoped>
.hdr {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
  gap: 16px;
}
.hdr__logo { font-weight: 700; }
.hdr__nav { display: flex; gap: 16px; flex: 1; }
.hdr__tab {
  text-decoration: none;
  color: var(--color-muted);
  padding: 6px 8px;
  border-radius: 4px;
}
.hdr__tab--active { color: var(--color-fg); font-weight: 600; }
.hdr__right { display: flex; gap: 8px; align-items: center; }
.hdr__icon,
.hdr__login {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-fg);
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
}
</style>
