<script setup lang="ts">
defineProps<{ message: string; actionLabel?: string }>()
defineEmits<{ (e: 'action'): void }>()
</script>
<template>
  <div class="empty">
    <div class="empty__icon" aria-hidden="true">∅</div>
    <p class="empty__msg">{{ message }}</p>
    <button v-if="actionLabel" class="empty__btn" type="button" @click="$emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>
<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 16px;
  color: var(--color-muted);
  text-align: center;
}
.empty__icon { font-size: 28px; }
.empty__msg { margin: 0; font-size: 14px; }
.empty__btn {
  background: var(--theme-primary, #2563eb);
  color: var(--theme-on-primary, #fff);
  border: 0;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
}
</style>
