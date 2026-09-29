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
  Category, DebateBrief, DebateDetail, Notification, Paginated,
  TokenResponse, User, VoteChoice,
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
  lock: (id: string) => api.post(`/debates/${id}/lock`).then(r => r.data),
  createInvitation: (id: string, body: Record<string, unknown>) =>
    api.post(`/debates/${id}/invitations`, body).then(r => r.data),
  share: (id: string) => api.get(`/debates/${id}/share`).then(r => r.data),
  acceptInvitation: (token: string) =>
    api.post('/debates/invitations/accept', null, { params: { token } }).then(r => r.data),
  declineInvitation: (token: string) =>
    api.post('/debates/invitations/decline', null, { params: { token } }).then(r => r.data),
  invitationDetails: (token: string) =>
    api.get<{ kind: string; debate_id: string; question: string; status: string }>(`/debates/invitations/${token}`).then(r => r.data),
}

export const categoriesApi = {
  list: () => api.get<Category[]>('/categories').then(r => r.data),
}

export interface CommentOut {
  id: string
  debate_id: string
  parent_id?: string | null
  user_id: string
  body: string
  username?: string | null
  created_at: string
  pinned?: boolean
  reactions?: Record<string, number>
}

export const commentsApi = {
  list: (debateId: string) =>
    api.get<CommentOut[]>(`/debates/${debateId}/comments`).then(r => r.data),
  create: (debateId: string, body: string, parentId?: string | null) =>
    api.post<CommentOut>(`/debates/${debateId}/comments`, { body, parent_id: parentId ?? null }).then(r => r.data),
  react: (debateId: string, commentId: string, reaction: string) =>
    api.put(`/debates/${debateId}/comments/${commentId}/reaction`, { reaction }).then(r => r.data),
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

export const mediaApi = {
  // Upload an image or video to a debate. Returns the created media record.
  upload: (file: File, kind: 'image' | 'video', debateId?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('kind', kind)
    if (debateId) form.append('debate_id', debateId)
    return api
      .post<{ id: string; kind: string; url: string; content_type: string; status: string }>('/media/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then(r => r.data)
  },
  // Upload a new profile picture; also updates the profile's avatar_url.
  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<{ id: string; url: string }>('/media/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then(r => r.data)
  },
  remove: (id: string) => api.delete(`/media/${id}`).then(r => r.data),
}

export const adminApi = {
  stats: () => api.get('/admin/stats').then(r => r.data),
  users: () => api.get('/admin/users').then(r => r.data),
  disputes: () => api.get('/disputes').then(r => r.data),
  resolveDispute: (id: string, body: Record<string, unknown>) => api.post(`/disputes/${id}/resolve`, body).then(r => r.data),
  submitSettlement: (body: Record<string, unknown>) => api.post('/admin/settlements/submit', body).then(r => r.data),
  auditLogs: () => api.get('/admin/audit-logs').then(r => r.data),
}
