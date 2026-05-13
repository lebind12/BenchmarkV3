<script setup lang="ts">
import CubeCarousel from './CubeCarousel.vue'
</script>
<template>
  <section class="left">
    <div class="left__logo">
      <span class="left__brand">⚽ 벤치마크</span>
    </div>
    <div class="left__cube"><CubeCarousel /></div>
  </section>
</template>
<style scoped>
.left { display: flex; flex-direction: column; height: 100%; border-right: 1px solid var(--color-border); }
.left__logo {
  flex: 0 0 30%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--color-border);
  font-size: 18px;
  font-weight: 700;
}
.left__brand { letter-spacing: 0.5px; }
.left__cube { flex: 1 1 70%; min-height: 0; }
</style>
