<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useHomeStore } from '@/stores/home'
import LeftPanel from '@/components/home/LeftPanel.vue'
import CenterPanel from '@/components/home/CenterPanel.vue'
import RightPanel from '@/components/home/RightPanel.vue'

const home = useHomeStore()

onMounted(() => {
  home.bootstrap()
})
onBeforeUnmount(() => {
  home.teardown()
})
</script>
<template>
  <div class="home" data-testid="home-view">
    <LeftPanel />
    <CenterPanel />
    <RightPanel />
  </div>
</template>
<style scoped>
.home {
  height: calc(100vh - var(--header-height));
  display: grid;
  grid-template-columns: 25% 50% 25%;
  overflow: hidden;
}
</style>
