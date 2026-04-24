import { create } from 'zustand'
import { authApi, tokenStore, type User } from './api'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<{ requires_totp: boolean; totp_token?: string }>
  completeTOTP: (totp_token: string, code: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: false,

  login: async (email, password) => {
    set({ loading: true })
    try {
      const { data } = await authApi.login(email, password)
      if (data.requires_totp) {
        set({ loading: false })
        return { requires_totp: true, totp_token: data.totp_token ?? undefined }
      }
      if (!data.access_token || !data.refresh_token) throw new Error('No tokens received')
      tokenStore.set(data.access_token, data.refresh_token)
      const { data: user } = await authApi.me()
      set({ user, loading: false })
      return { requires_totp: false }
    } catch (err) {
      set({ loading: false })
      throw err
    }
  },

  completeTOTP: async (totp_token, code) => {
    set({ loading: true })
    try {
      const { data } = await authApi.totpVerifyLogin(totp_token, code)
      tokenStore.set(data.access_token, data.refresh_token)
      const { data: user } = await authApi.me()
      set({ user, loading: false })
    } catch (err) {
      set({ loading: false })
      throw err
    }
  },

  logout: () => {
    tokenStore.clear()
    set({ user: null })
    window.location.href = '/login'
  },

  loadUser: async () => {
    if (!tokenStore.getAccess()) return
    set({ loading: true })
    try {
      const { data } = await authApi.me()
      set({ user: data, loading: false })
    } catch {
      tokenStore.clear()
      set({ loading: false })
    }
  },
}))
