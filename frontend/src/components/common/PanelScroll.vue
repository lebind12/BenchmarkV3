<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ fade?: boolean }>(), { fade: true })
const showFade = computed(() => props.fade !== false)
</script>
<template>
  <div class="panel-scroll-wrap">
    <div class="panel-scroll" data-testid="panel-scroll">
      <slot />
    </div>
    <div v-if="showFade" class="panel-scroll-fade" data-testid="panel-scroll-fade" />
  </div>
</template>
