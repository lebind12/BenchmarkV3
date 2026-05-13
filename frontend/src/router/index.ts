import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const PlaceholderView = {
  template: '<main style="padding:24px"><h2>{{ title }}</h2><p>(placeholder)</p></main>',
  props: ['title'],
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: DefaultLayout,
    children: [
      { path: '', name: 'home', component: () => import('@/views/HomeView.vue') },
      { path: 'fixtures', name: 'fixtures', component: PlaceholderView, props: { title: '경기' } },
      { path: 'fixtures/:id', name: 'fixture-detail', component: PlaceholderView, props: { title: '경기 상세' } },
      { path: 'standings', name: 'standings', component: PlaceholderView, props: { title: '순위' } },
      { path: 'teams', name: 'teams', component: PlaceholderView, props: { title: '팀' } },
      { path: 'teams/:slug', name: 'team-detail', component: PlaceholderView, props: { title: '팀 상세' } },
      { path: 'players', name: 'players', component: PlaceholderView, props: { title: '선수' } },
      { path: 'players/:slug', name: 'player-detail', component: PlaceholderView, props: { title: '선수 상세' } },
      { path: 'stats', name: 'stats', component: PlaceholderView, props: { title: '스탯' } },
      { path: 'broadcast', name: 'broadcast', component: PlaceholderView, props: { title: '방송' } },
      { path: 'auth/login', name: 'login', component: PlaceholderView, props: { title: '로그인' } },
    ],
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})
