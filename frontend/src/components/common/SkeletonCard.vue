<script setup lang="ts">
defineProps<{ height?: number }>()
</script>
<template>
  <div class="sk" :style="{ height: (height ?? 64) + 'px' }" aria-hidden="true" />
</template>
<style scoped>
.sk {
  background: linear-gradient(90deg, var(--color-card), var(--color-card-hover), var(--color-card));
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
  border-radius: 8px;
  margin-bottom: 8px;
}
@keyframes shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
</style>
