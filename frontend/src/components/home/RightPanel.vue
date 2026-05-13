<script setup lang="ts">
import StandingsBlock from './StandingsBlock.vue'
import TopPlayersBlock from './TopPlayersBlock.vue'
</script>
<template>
  <aside class="right" data-testid="right-panel">
    <div class="right__top"><StandingsBlock /></div>
    <div class="right__bot"><TopPlayersBlock /></div>
  </aside>
</template>
<style scoped>
.right {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-left: 1px solid var(--color-border);
}
.right__top, .right__bot { flex: 1 1 50%; min-height: 0; }
.right__top { border-bottom: 1px solid var(--color-border); }
</style>
