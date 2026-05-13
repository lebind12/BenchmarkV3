<script setup lang="ts">
import { onMounted } from 'vue'
import AppHeader from '@/components/common/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(() => {
  auth.hydrateFromMock()
  const stored = localStorage.getItem('theme')
  const prefersDark =
    !stored && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-color-scheme: dark)').matches
  if (stored === 'dark' || prefersDark) document.documentElement.classList.add('dark')
})
</script>
<template>
  <AppHeader />
  <router-view />
</template>
