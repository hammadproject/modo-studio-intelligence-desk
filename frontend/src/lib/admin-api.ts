import { ApiError } from './api'
import type {
  AdminConversationDetail,
  AdminConversationPage,
  AdminSession,
  HistoryMessage,
  SupportStatus,
} from '../types/api'

const DEFAULT_API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError('The operator inbox could not reach the API.', 0, 'network_error')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as {
      error?: { message?: string; code?: string }
    }
    throw new ApiError(
      payload.error?.message || `Request failed with status ${response.status}`,
      response.status,
      payload.error?.code,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const adminApi = {
  login: (apiKey: string) => adminRequest<AdminSession>('/api/v1/admin/session', {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey }),
  }),
  session: () => adminRequest<AdminSession>('/api/v1/admin/session'),
  logout: () => adminRequest<void>('/api/v1/admin/session', { method: 'DELETE' }),
  conversations: (options: {
    supportStatus?: string
    search?: string
    scope?: 'inbox' | 'history'
    timeWindow?: string
    cursor?: string | null
  } = {}) => {
    const params = new URLSearchParams()
    const supportStatus = options.supportStatus || 'all'
    const search = options.search || ''
    if (supportStatus !== 'all') params.set('support_status', supportStatus)
    if (search.trim()) params.set('search', search.trim())
    params.set('scope', options.scope || 'inbox')
    params.set('time_window', options.timeWindow || '1d')
    if (options.cursor) params.set('cursor', options.cursor)
    return adminRequest<AdminConversationPage>(`/api/v1/admin/conversations?${params}`)
  },
  conversation: (conversationId: string) =>
    adminRequest<AdminConversationDetail>(`/api/v1/admin/conversations/${conversationId}`),
  takeover: (conversationId: string) =>
    adminRequest(`/api/v1/admin/conversations/${conversationId}/takeover`, { method: 'POST' }),
  release: (conversationId: string) =>
    adminRequest(`/api/v1/admin/conversations/${conversationId}/release`, { method: 'POST' }),
  resolve: (conversationId: string) =>
    adminRequest(`/api/v1/admin/conversations/${conversationId}/resolve`, { method: 'POST' }),
  reply: (conversationId: string, message: string) =>
    adminRequest<HistoryMessage>(`/api/v1/admin/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
}

export const supportLabels: Record<SupportStatus, string> = {
  ai_active: 'Ren handling',
  waiting_for_human: 'Waiting for human',
  human_active: 'Human active',
  resolved: 'Resolved',
  archived: 'Archived',
}
