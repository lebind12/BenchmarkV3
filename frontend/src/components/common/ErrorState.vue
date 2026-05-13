<script setup lang="ts">
defineProps<{ message?: string }>()
defineEmits<{ (e: 'retry'): void }>()
</script>
<template>
  <div class="err" role="alert">
    <p class="err__msg">{{ message ?? '데이터를 불러오지 못했습니다.' }}</p>
    <button class="err__btn" type="button" @click="$emit('retry')">다시 시도</button>
  </div>
</template>
<style scoped>
.err {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  padding: 24px 16px;
  color: var(--color-muted);
  text-align: center;
}
.err__btn {
  background: transparent;
  color: var(--color-fg);
  border: 1px solid var(--color-border);
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
}
</style>
