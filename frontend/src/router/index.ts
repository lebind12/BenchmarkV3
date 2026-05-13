import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { defineComponent, h } from 'vue'
import { useRoute } from 'vue-router'

const PlayerStub = defineComponent({
  name: 'PlayerStub',
  setup() {
    const r = useRoute()
    return () =>
      h('div', { 'data-testid': 'player-stub' }, `player ${r.params.slug}`)
  },
})

const TeamStub = defineComponent({
  name: 'TeamStub',
  setup() {
    const r = useRoute()
    return () =>
      h('div', { 'data-testid': 'team-stub' }, `team ${r.params.slug}`)
  },
})

const NotFound = defineComponent({
  name: 'NotFound',
  setup() {
    return () =>
      h(
        'div',
        { 'data-testid': 'not-found' },
        '존재하지 않는 경기입니다 → 메인으로',
      )
  },
})

const HomeStub = defineComponent({
  name: 'HomeStub',
  setup() {
    return () => h('div', { 'data-testid': 'home-stub' }, 'main-home placeholder')
  },
})

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: HomeStub,
  },
  {
    path: '/fixtures/:externalId(\\d+)',
    name: 'fixture-detail',
    component: () => import('@/views/FixtureDetailView.vue'),
    meta: { layout: 'default', title: '매치' },
  },
  {
    path: '/players/:slug',
    name: 'player-detail',
    component: PlayerStub,
  },
  {
    path: '/teams/:slug',
    name: 'team-detail',
    component: TeamStub,
  },
  {
    path: '/not-found',
    name: 'not-found',
    component: NotFound,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/not-found',
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
