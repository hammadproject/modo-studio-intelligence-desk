import type {
  ApiErrorPayload,
  ChatOutput,
  ConversationCreated,
  HandoffInput,
  HandoffOutput,
  MessagePage,
  ReadinessOutput,
  VisitorConversationPage,
} from '../types/api'

const DEFAULT_API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(
    message: string,
    status: number,
    code = 'request_failed',
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
    throw new ApiError(
      'Unable to reach the Modo Studio assistant. Check your connection and try again.',
      0,
      'network_error',
    )
  }

  if (!response.ok) {
    let payload: ApiErrorPayload = {}
    try {
      payload = (await response.json()) as ApiErrorPayload
    } catch {
      // Use the typed HTTP fallback below when the response is not JSON.
    }
    throw new ApiError(
      payload.error?.message || `Request failed with status ${response.status}`,
      response.status,
      payload.error?.code,
    )
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const modoDeskApi = {
  readiness: () => request<ReadinessOutput>('/health/ready'),
  createConversation: () =>
    request<ConversationCreated>('/api/v1/conversations', { method: 'POST' }),
  sendMessage: (
    conversationId: string,
    requestId: string,
    message: string,
  ) =>
    request<ChatOutput>(`/api/v1/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, message }),
    }),
  streamMessage: async (
    conversationId: string,
    requestId: string,
    message: string,
    onDelta: (delta: string) => void,
  ): Promise<ChatOutput> => {
    let response: Response
    try {
      response = await fetch(
        `${API_BASE_URL}/api/v1/conversations/${conversationId}/messages/stream`,
        {
          method: 'POST',
          credentials: 'include',
          headers: {
            Accept: 'text/event-stream',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ request_id: requestId, message }),
        },
      )
    } catch {
      throw new ApiError(
        'Unable to reach the Modo Studio assistant. Check your connection and try again.',
        0,
        'network_error',
      )
    }

    if (!response.ok) {
      let payload: ApiErrorPayload = {}
      try {
        payload = (await response.json()) as ApiErrorPayload
      } catch {
        // Use the HTTP fallback below when the response is not JSON.
      }
      throw new ApiError(
        payload.error?.message || `Request failed with status ${response.status}`,
        response.status,
        payload.error?.code,
      )
    }
    if (!response.body) {
      throw new ApiError('The assistant returned an unreadable response stream.', 0, 'stream_unavailable')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let completed: ChatOutput | null = null

    function processBlock(block: string) {
      let eventName = 'message'
      const dataLines: string[] = []
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
      }
      if (!dataLines.length) return
      const payload = JSON.parse(dataLines.join('\n')) as {
        delta?: string
        response?: ChatOutput
        error?: { code?: string; message?: string }
      }
      if (eventName === 'delta' && payload.delta) onDelta(payload.delta)
      if (eventName === 'complete' && payload.response) completed = payload.response
      if (eventName === 'error') {
        throw new ApiError(
          payload.error?.message || 'The assistant could not complete the response.',
          0,
          payload.error?.code,
        )
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let boundary = buffer.match(/\r?\n\r?\n/)
      while (boundary?.index !== undefined) {
        processBlock(buffer.slice(0, boundary.index))
        buffer = buffer.slice(boundary.index + boundary[0].length)
        boundary = buffer.match(/\r?\n\r?\n/)
      }
      if (done) break
    }
    if (buffer.trim()) processBlock(buffer)
    if (!completed) {
      throw new ApiError('The assistant response ended before completion.', 0, 'incomplete_stream')
    }
    return completed
  },
  history: (conversationId: string) =>
    request<MessagePage>(`/api/v1/conversations/${conversationId}/messages?limit=100`),
  visitorConversations: () =>
    request<VisitorConversationPage>('/api/v1/visitor/conversations'),
  claimConversation: (conversationId: string, accessToken: string) =>
    request<void>('/api/v1/visitor/conversations/claim', {
      method: 'POST',
      body: JSON.stringify({ conversation_id: conversationId, access_token: accessToken }),
    }),
  presence: (conversationId: string) =>
    request<{ conversation_id: string; last_seen_at: string }>(
      `/api/v1/conversations/${conversationId}/presence`,
      { method: 'POST' },
    ),
  createHandoff: (
    conversationId: string,
    input: HandoffInput,
  ) =>
    request<HandoffOutput>(`/api/v1/conversations/${conversationId}/handoffs`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
}
