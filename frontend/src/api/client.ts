// Axios API client. Attaches the access token and surfaces friendly errors (§73).
import axios, { AxiosError } from 'axios'
import type { ApiError } from '../types'

const baseURL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

export const api = axios.create({ baseURL, timeout: 20000 })

const TOKEN_KEY = 'ds_access_token'
const REFRESH_KEY = 'ds_refresh_token'

export const tokenStore = {
  get access() { return localStorage.getItem(TOKEN_KEY) },
  get refresh() { return localStorage.getItem(REFRESH_KEY) },
  set(access: string, refresh: string) {
    localStorage.setItem(TOKEN_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

api.interceptors.request.use((config) => {
  const token = tokenStore.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Extract a user-friendly message from an API error.
export function friendlyError(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as ApiError | undefined
    if (data?.error?.message) return data.error.message
    if (err.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
    if (!err.response) return 'Cannot reach the server. Check your connection.'
  }
  if (err instanceof Error && err.message) return err.message
  return fallback
}

// Typed API surface -------------------------------------------------------

import type {
  Category, DebateBrief, DebateDetail, Notification, Paginated, ProviderOption,
  StakePreview, TokenResponse, Transaction, User, VoteChoice, Wallet,
} from '../types'

export const authApi = {
  register: (body: Record<string, unknown>) => api.post<User>('/auth/register', body).then(r => r.data),
  login: (identifier: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { identifier, password }).then(r => r.data),
  me: () => api.get<User>('/auth/me').then(r => r.data),
  usernameCheck: (username: string) =>
    api.post<{ available: boolean }>('/auth/username-check', { username }).then(r => r.data),
  forgotPassword: (email: string) => api.post<{ message: string }>('/auth/forgot-password', { email }).then(r => r.data),
  resetPassword: (token: string, new_password: string) =>
    api.post<{ message: string }>('/auth/reset-password', { token, new_password }).then(r => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.post<{ message: string }>('/auth/change-password', { current_password, new_password }).then(r => r.data),
}

export const debatesApi = {
  list: (params: Record<string, unknown> = {}) =>
    api.get<Paginated<DebateBrief>>('/debates', { params }).then(r => r.data),
  trending: () => api.get<DebateBrief[]>('/debates/trending').then(r => r.data),
  search: (q: string, params: Record<string, unknown> = {}) =>
    api.get<Paginated<DebateBrief>>('/debates/search', { params: { q, ...params } }).then(r => r.data),
  get: (id: string) => api.get<DebateDetail>(`/debates/${id}`).then(r => r.data),
  create: (body: Record<string, unknown>) => api.post<DebateDetail>('/debates', body).then(r => r.data),
  vote: (id: string, choice: VoteChoice) =>
    api.post(`/debates/${id}/vote`, { choice }).then(r => r.data),
  confirm: (id: string, side: 'a' | 'b') => api.post(`/debates/${id}/confirm`, { side }).then(r => r.data),
  fund: (id: string) => api.post(`/debates/${id}/fund`).then(r => r.data),
  lock: (id: string) => api.post(`/debates/${id}/lock`).then(r => r.data),
  stakePreview: (id: string) => api.get<StakePreview>(`/debates/${id}/stake-preview`).then(r => r.data),
  createInvitation: (id: string, body: Record<string, unknown>) =>
    api.post(`/debates/${id}/invitations`, body).then(r => r.data),
  share: (id: string) => api.get(`/debates/${id}/share`).then(r => r.data),
  acceptInvitation: (token: string) =>
    api.post('/debates/invitations/accept', null, { params: { token } }).then(r => r.data),
}

export const walletApi = {
  get: () => api.get<Wallet>('/wallet').then(r => r.data),
  transactions: (params: Record<string, unknown> = {}) =>
    api.get<Paginated<Transaction>>('/wallet/transactions', { params }).then(r => r.data),
  stakePreview: (amount: number) =>
    api.get<StakePreview>('/wallet/stake-preview', { params: { amount } }).then(r => r.data),
  providers: (for_payout = false) =>
    api.get<ProviderOption[]>('/payments/providers', { params: { for_payout } }).then(r => r.data),
  deposit: (body: Record<string, unknown>) => api.post('/deposits', body).then(r => r.data),
  withdrawalQuote: (amount: number) =>
    api.get('/withdrawals/quote', { params: { amount } }).then(r => r.data),
  withdraw: (body: Record<string, unknown>) => api.post('/withdrawals', body).then(r => r.data),
  listWithdrawals: () => api.get('/withdrawals').then(r => r.data),
}

export const categoriesApi = {
  list: () => api.get<Category[]>('/categories').then(r => r.data),
}

export const notificationsApi = {
  list: () => api.get<Notification[]>('/notifications').then(r => r.data),
  markRead: (id: string) => api.post(`/notifications/${id}/read`).then(r => r.data),
  markAllRead: () => api.post('/notifications/read-all').then(r => r.data),
}

export const usersApi = {
  me: () => api.get<User>('/users/me').then(r => r.data),
  updateProfile: (body: Record<string, unknown>) => api.patch<User>('/users/me/profile', body).then(r => r.data),
  getPreferences: () => api.get('/users/me/preferences').then(r => r.data),
  updatePreferences: (body: Record<string, unknown>) => api.patch('/users/me/preferences', body).then(r => r.data),
}

export const disputesApi = {
  create: (body: Record<string, unknown>) => api.post('/disputes', body).then(r => r.data),
  mine: () => api.get('/disputes/mine').then(r => r.data),
}

export const gamesApi = {
  types: () => api.get<string[]>('/games/types').then(r => r.data),
  create: (game_type: string) => api.post('/games', { game_type }).then(r => r.data),
  list: () => api.get('/games').then(r => r.data),
}

export const adminApi = {
  stats: () => api.get('/admin/stats').then(r => r.data),
  users: () => api.get('/admin/users').then(r => r.data),
  disputes: () => api.get('/disputes').then(r => r.data),
  resolveDispute: (id: string, body: Record<string, unknown>) => api.post(`/disputes/${id}/resolve`, body).then(r => r.data),
  submitSettlement: (body: Record<string, unknown>) => api.post('/admin/settlements/submit', body).then(r => r.data),
  auditLogs: () => api.get('/admin/audit-logs').then(r => r.data),
}
