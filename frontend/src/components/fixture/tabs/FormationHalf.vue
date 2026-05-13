<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { TeamLineup } from '@/types/fixtureDetail'
import { resolveFormation } from '@/lib/formations'

const props = defineProps<{
  lineup: TeamLineup
  side: 'home' | 'away'
}>()

const router = useRouter()

// Lay out start_xi over lines from formation.
const lines = computed(() => {
  const counts = resolveFormation(props.lineup.formation)
  const players = [...props.lineup.start_xi]
  const grouped: Array<Array<(typeof players)[number]>> = []
  let i = 0
  for (const c of counts) {
    grouped.push(players.slice(i, i + c))
    i += c
  }
  return grouped
})

// fallback when formation string is null but start_xi exists
const useFallbackGrid = computed(
  () => props.lineup.formation == null && props.lineup.start_xi.length > 0,
)

function go(slug: string) {
  void router.push(`/players/${slug}`)
}
</script>

<template>
  <div
    class="formation-half"
    :data-side="side"
    :data-testid="`formation-half-${side}`"
  >
    <header class="formation-half__head">
      <strong>{{ side === 'home' ? '홈' : '어웨이' }}</strong>
      <span v-if="lineup.formation">{{ lineup.formation }}</span>
    </header>

    <div
      v-if="useFallbackGrid"
      class="formation-half__fallback"
      data-testid="formation-fallback"
    >
      <button
        v-for="p in lineup.start_xi"
        :key="p.player.external_id"
        type="button"
        class="formation-node"
        @click="go(p.player.slug)"
      >
        <span class="formation-node__num">{{ p.number }}</span>
        <span class="formation-node__name">{{
          p.player.name_ko ?? p.player.name
        }}</span>
      </button>
    </div>

    <div v-else class="formation-half__lines">
      <div
        v-for="(line, i) in lines"
        :key="i"
        class="formation-half__line"
      >
        <button
          v-for="p in line"
          :key="p.player.external_id"
          type="button"
          class="formation-node"
          :data-testid="`formation-node-${side}`"
          :title="
            p.rating != null
              ? `평점 ${p.rating.toFixed(1)} · ${p.minutes ?? 0}분`
              : undefined
          "
          @click="go(p.player.slug)"
        >
          <span class="formation-node__num">{{ p.number }}</span>
          <span class="formation-node__name">{{
            p.player.name_ko ?? p.player.name
          }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.formation-half {
  display: flex;
  flex-direction: column;
  padding: 0.5rem;
  height: 100%;
  box-sizing: border-box;
}
.formation-half__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 0.8rem;
  color: var(--muted-foreground);
  padding-bottom: 0.5rem;
}
.formation-half__lines {
  display: flex;
  flex-direction: column-reverse;
  justify-content: space-around;
  flex: 1;
}
.formation-half[data-side='away'] .formation-half__lines {
  flex-direction: column;
}
.formation-half__line {
  display: flex;
  justify-content: space-around;
  gap: 0.25rem;
}
.formation-half__fallback {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.25rem;
}
.formation-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  padding: 0.3rem 0.4rem;
  background: color-mix(in srgb, var(--theme-primary) 15%, transparent);
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  min-width: 3rem;
  max-width: 5rem;
}
.formation-node__num {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--theme-on-primary);
  background: var(--theme-primary);
  border-radius: 50%;
  width: 1.4rem;
  height: 1.4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.formation-node__name {
  font-size: 0.7rem;
  color: var(--foreground);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 4.5rem;
}
</style>
