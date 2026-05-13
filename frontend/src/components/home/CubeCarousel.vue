<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useHomeStore } from '@/stores/home'
import CubeNewsFace from './faces/CubeNewsFace.vue'
import CubeHotPlayerFace from './faces/CubeHotPlayerFace.vue'
import CubeTransferFace from './faces/CubeTransferFace.vue'
import CubeInjuryFace from './faces/CubeInjuryFace.vue'

const home = useHomeStore()

const faceLabels = ['뉴스', '핫', '이적', '부상'] as const
const stageRef = ref<HTMLElement | null>(null)
const faceZ = ref(200)

function recalcZ() {
  if (!stageRef.value) return
  const w = stageRef.value.clientWidth
  faceZ.value = Math.max(120, Math.floor(w / 2))
}

let ro: ResizeObserver | null = null
onMounted(() => {
  recalcZ()
  if (typeof ResizeObserver !== 'undefined' && stageRef.value) {
    ro = new ResizeObserver(recalcZ)
    ro.observe(stageRef.value)
  }
})
onBeforeUnmount(() => {
  ro?.disconnect()
})

function onEnter() { home.pauseAutoRotate() }
function onLeave() { home.resumeAutoRotate() }
function selectFace(i: 0 | 1 | 2 | 3) { home.setFace(i) }

function onKey(e: KeyboardEvent) {
  if (e.key === 'ArrowRight') {
    selectFace(((home.cube.activeFace + 1) % 4) as 0 | 1 | 2 | 3)
    e.preventDefault()
  } else if (e.key === 'ArrowLeft') {
    selectFace(((home.cube.activeFace + 3) % 4) as 0 | 1 | 2 | 3)
    e.preventDefault()
  }
}

const rotation = computed(() => `rotateY(${-90 * home.cube.activeFace}deg)`)
</script>
<template>
  <div
    class="cube-wrap"
    role="region"
    aria-roledescription="carousel"
    aria-label="홈 큐브"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
    @focusin="onEnter"
    @focusout="onLeave"
  >
    <div
      ref="stageRef"
      class="cube-stage"
      :style="{ '--face-z': faceZ + 'px' }"
      aria-live="polite"
    >
      <div class="cube" :style="{ transform: rotation }" data-testid="cube">
        <div
          v-for="(label, i) in faceLabels"
          :key="i"
          class="face"
          :class="`face-${i}`"
          role="group"
          aria-roledescription="slide"
          :aria-label="label"
          :aria-hidden="home.cube.activeFace !== i"
          :inert="home.cube.activeFace !== i"
          :data-testid="`cube-face-${i}`"
        >
          <CubeNewsFace v-if="i === 0" />
          <CubeHotPlayerFace v-else-if="i === 1" />
          <CubeTransferFace v-else-if="i === 2" />
          <CubeInjuryFace v-else />
        </div>
      </div>
    </div>
    <div
      class="dots"
      role="tablist"
      aria-label="큐브 페이지"
      data-testid="cube-dots"
      @keydown="onKey"
    >
      <button
        v-for="(label, i) in faceLabels"
        :key="i"
        type="button"
        role="tab"
        :aria-selected="home.cube.activeFace === i"
        :tabindex="home.cube.activeFace === i ? 0 : -1"
        :class="['dot', { 'dot--active': home.cube.activeFace === i }]"
        :data-testid="`cube-dot-${i}`"
        @click="selectFace(i as 0 | 1 | 2 | 3)"
      >
        <span class="dot__pill" aria-hidden="true" />
        <span class="dot__label">{{ label }}</span>
      </button>
    </div>
  </div>
</template>
<style scoped>
.cube-wrap {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 8px;
  box-sizing: border-box;
}
.cube-stage {
  flex: 1;
  perspective: 1000px;
  position: relative;
  min-height: 0;
}
.cube {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.8s cubic-bezier(0.65, 0.05, 0.36, 1);
}
.face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  overflow: hidden;
  box-sizing: border-box;
}
.face-0 { transform: rotateY(0deg) translateZ(var(--face-z)); }
.face-1 { transform: rotateY(90deg) translateZ(var(--face-z)); }
.face-2 { transform: rotateY(180deg) translateZ(var(--face-z)); }
.face-3 { transform: rotateY(270deg) translateZ(var(--face-z)); }

.dots {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 8px 0 0;
}
.dot {
  background: transparent;
  border: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--color-muted);
}
.dot__pill {
  display: block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-border);
}
.dot--active .dot__pill { background: var(--theme-primary, var(--color-fg)); transform: scale(1.2); }
.dot--active { color: var(--color-fg); font-weight: 600; }
.dot__label { font-size: 11px; }
</style>
