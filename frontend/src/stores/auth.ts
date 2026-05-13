import { defineStore } from 'pinia'

export type Role = 'public' | 'USER' | 'STREAMER' | 'ADMIN'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    role: 'public' as Role,
  }),
  getters: {
    isStreamer: (s) => s.role === 'STREAMER',
    isLoggedIn: (s) => s.role !== 'public',
  },
  actions: {
    hydrateFromMock() {
      const v = (typeof localStorage !== 'undefined' && localStorage.getItem('mockRole')) || 'public'
      if (v === 'public' || v === 'USER' || v === 'STREAMER' || v === 'ADMIN') this.role = v
    },
    setRole(r: Role) {
      this.role = r
      if (typeof localStorage !== 'undefined') localStorage.setItem('mockRole', r)
    },
  },
})
