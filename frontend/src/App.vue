<script setup lang="ts">
</script>

<template>
  <div class="app-shell">
    <header class="app-header" data-testid="app-header">
      <strong>축구 정보</strong>
    </header>
    <router-view />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.app-header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 1rem;
  border-bottom: 1px solid var(--muted);
  font-family: system-ui, -apple-system, sans-serif;
  color: var(--foreground);
}
</style>
<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  color: var(--foreground);
}
body {
  overflow: hidden;
}
</style>
