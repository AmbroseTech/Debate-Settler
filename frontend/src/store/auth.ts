// Auth store (Zustand) with localStorage persistence (§68 store/).
import { create } from 'zustand'
import { authApi, tokenStore } from '../api/client'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  initialized: boolean
  login: (identifier: string, password: string) => Promise<void>
  register: (body: Record<string, unknown>) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  login: async (identifier, password) => {
    set({ loading: true })
    try {
      const tokens = await authApi.login(identifier, password)
      tokenStore.set(tokens.access_token, tokens.refresh_token)
      const user = await authApi.me()
      set({ user, initialized: true })
    } finally {
      set({ loading: false })
    }
  },

  register: async (body) => {
    set({ loading: true })
    try {
      await authApi.register(body)
      const tokens = await authApi.login(body.email as string, body.password as string)
      tokenStore.set(tokens.access_token, tokens.refresh_token)
      const user = await authApi.me()
      set({ user, initialized: true })
    } finally {
      set({ loading: false })
    }
  },

  logout: () => {
    tokenStore.clear()
    set({ user: null })
  },

  loadUser: async () => {
    if (!tokenStore.access) {
      set({ initialized: true })
      return
    }
    try {
      const user = await authApi.me()
      set({ user, initialized: true })
    } catch {
      tokenStore.clear()
      set({ user: null, initialized: true })
    }
  },
}))
