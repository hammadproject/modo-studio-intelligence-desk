/* oxlint-disable react/only-export-components -- The provider and its consumer hook share one private context. */
/* oxlint-disable react/set-state-in-effect -- Effects restore server-owned history and presence. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { ApiError, modoDeskApi } from '../lib/api'
import { playReceiveSound, playSendSound } from '../lib/chat-sounds'
import { plainTextPreview } from '../lib/chat-text'
import type { HandoffInput, ReadinessOutput, SourceCitation } from '../types/api'

const ACTIVE_STORAGE_KEY = 'modo.activeConversation.v2'
const LEGACY_ACTIVE_KEY = 'modo.chirpy.session.v1'
const LEGACY_HISTORY_KEY = 'modo.chirpy.conversations.v1'

interface ChatSession {
  conversationId: string
}

export interface ConversationSummary extends ChatSession {
  title: string
  preview: string
  updatedAt: string
}

export interface UiMessage {
  id: string
  role: 'user' | 'assistant' | 'operator' | 'system'
  sequence?: number
  content: string
  createdAt: string
  requestId?: string
  status: 'pending' | 'streaming' | 'sent' | 'failed'
  sources?: SourceCitation[]
}

interface ChatContextValue {
  messages: UiMessage[]
  conversations: ConversationSummary[]
  activeConversationId: string | null
  isSending: boolean
  isLoadingHistory: boolean
  error: string | null
  health: ReadinessOutput | null
  sendMessage: (message: string, requestId?: string) => Promise<boolean>
  retryMessage: (requestId: string) => Promise<void>
  newChat: () => void
  selectConversation: (conversationId: string) => Promise<void>
  refreshHealth: () => Promise<void>
  submitHandoff: (input: HandoffInput) => Promise<'recorded'>
}

const ChatContext = createContext<ChatContextValue | null>(null)

function storedActiveId() {
  try {
    return localStorage.getItem(ACTIVE_STORAGE_KEY)
  } catch {
    return null
  }
}

function legacySessions(): Array<{ conversationId: string; accessToken: string }> {
  try {
    const active = JSON.parse(sessionStorage.getItem(LEGACY_ACTIVE_KEY) || 'null') as {
      conversationId?: string
      accessToken?: string
    } | null
    const history = JSON.parse(sessionStorage.getItem(LEGACY_HISTORY_KEY) || '[]') as Array<{
      conversationId?: string
      accessToken?: string
    }>
    const found = [active, ...history].filter((item): item is {
      conversationId: string
      accessToken: string
    } => Boolean(item?.conversationId && item?.accessToken))
    return found.filter((item, index) => found.findIndex(
      (candidate) => candidate.conversationId === item.conversationId,
    ) === index)
  } catch {
    return []
  }
}

function persistActiveId(id: string | null) {
  try {
    if (id) localStorage.setItem(ACTIVE_STORAGE_KEY, id)
    else localStorage.removeItem(ACTIVE_STORAGE_KEY)
    sessionStorage.removeItem(LEGACY_ACTIVE_KEY)
    sessionStorage.removeItem(LEGACY_HISTORY_KEY)
  } catch {
    // Storage is optional; the HttpOnly visitor cookie remains authoritative.
  }
}

function threadPreview(message: string) {
  return plainTextPreview(message)
}

function mapHistory(items: Awaited<ReturnType<typeof modoDeskApi.history>>['items']): UiMessage[] {
  return items
    .filter((item) => ['user', 'assistant', 'operator', 'system'].includes(item.role))
    .map((item) => ({
      id: item.id,
      role: item.role as UiMessage['role'],
      sequence: item.sequence,
      content: item.content,
      createdAt: item.created_at,
      status: 'sent' as const,
      sources: item.metadata?.sources || [],
    }))
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<ChatSession | null>(null)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const sessionRef = useRef<ChatSession | null>(null)
  const creatingSession = useRef<Promise<ChatSession> | null>(null)
  const restoreVersion = useRef(0)
  const newestSequence = useRef(0)
  const [messages, setMessages] = useState<UiMessage[]>([])
  const [isSending, setIsSending] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [health, setHealth] = useState<ReadinessOutput | null>(null)

  const replaceSession = useCallback((next: ChatSession | null) => {
    sessionRef.current = next
    setSession(next)
    persistActiveId(next?.conversationId || null)
  }, [])

  const updateConversations = useCallback(
    (updater: (current: ConversationSummary[]) => ConversationSummary[]) => {
      setConversations((current) => updater(current)
        .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt)))
    },
    [],
  )

  const upsertConversation = useCallback((
    active: ChatSession,
    values: { preview?: string; updatedAt?: string },
  ) => {
    updateConversations((current) => {
      const existing = current.find((item) => item.conversationId === active.conversationId)
      return [{
        ...active,
        title: 'Ren',
        preview: values.preview ?? existing?.preview ?? 'No messages yet',
        updatedAt: values.updatedAt ?? new Date().toISOString(),
      }, ...current.filter((item) => item.conversationId !== active.conversationId)]
    })
  }, [updateConversations])

  const restoreHistory = useCallback(async (active: ChatSession) => {
    const version = ++restoreVersion.current
    setIsLoadingHistory(true)
    setError(null)
    try {
      const page = await modoDeskApi.history(active.conversationId)
      if (version !== restoreVersion.current) return
      const restored = mapHistory(page.items)
      newestSequence.current = Math.max(0, ...restored.map((item) => item.sequence || 0))
      setMessages(restored)
      const last = restored.at(-1)
      upsertConversation(active, last ? { preview: threadPreview(last.content) } : {})
    } catch (caught) {
      if (version !== restoreVersion.current) return
      if (caught instanceof ApiError && [401, 403, 404].includes(caught.status)) {
        updateConversations((current) => current.filter(
          (item) => item.conversationId !== active.conversationId,
        ))
        if (sessionRef.current?.conversationId === active.conversationId) replaceSession(null)
        setMessages([])
        setError('That previous chat is no longer available.')
      } else {
        setError('We could not restore that conversation. Please try again.')
      }
    } finally {
      if (version === restoreVersion.current) setIsLoadingHistory(false)
    }
  }, [replaceSession, updateConversations, upsertConversation])

  const refreshConversationList = useCallback(async () => {
    try {
      const page = await modoDeskApi.visitorConversations()
      const next = page.items.map((item) => ({
        conversationId: item.conversation_id,
        title: 'Ren',
        preview: threadPreview(item.preview),
        updatedAt: item.updated_at,
      }))
      setConversations(next)
      return next
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setConversations([])
        return []
      }
      throw caught
    }
  }, [])

  const ensureSession = useCallback(async () => {
    if (sessionRef.current) return sessionRef.current
    if (!creatingSession.current) {
      creatingSession.current = modoDeskApi.createConversation().then((created) => {
        const next = { conversationId: created.conversation_id }
        replaceSession(next)
        upsertConversation(next, { updatedAt: created.created_at })
        return next
      }).finally(() => {
        creatingSession.current = null
      })
    }
    return creatingSession.current
  }, [replaceSession, upsertConversation])

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await modoDeskApi.readiness())
    } catch {
      setHealth(null)
    }
  }, [])

  useEffect(() => {
    void refreshHealth()
    let cancelled = false
    const bootstrap = async () => {
      try {
        const legacy = legacySessions()
        for (const oldSession of legacy) {
          await modoDeskApi.claimConversation(
            oldSession.conversationId,
            oldSession.accessToken,
          ).catch(() => undefined)
        }
        const restored = await refreshConversationList()
        if (cancelled) return
        const preferredId = storedActiveId()
        const selected = restored.find((item) => item.conversationId === preferredId)
          || restored[0]
          || null
        if (selected) {
          replaceSession(selected)
          await restoreHistory(selected)
        } else {
          replaceSession(null)
          setIsLoadingHistory(false)
        }
      } catch {
        if (!cancelled) {
          setError('We could not restore your conversations. You can still start a new chat.')
          setIsLoadingHistory(false)
        }
      }
    }
    void bootstrap()
    return () => { cancelled = true }
  }, [refreshConversationList, refreshHealth, replaceSession, restoreHistory])

  const sendMessage = useCallback(async (rawMessage: string, suppliedRequestId?: string) => {
    const content = rawMessage.trim()
    if (!content || isSending) return false
    const requestId = suppliedRequestId || crypto.randomUUID()
    const assistantPlaceholderId = `assistant-${requestId}`
    const turnCreatedAt = new Date().toISOString()
    let receiveSoundPlayed = false
    playSendSound()
    setError(null)
    setIsSending(true)
    setMessages((current) => {
      const previousRemoved = current.filter(
        (message) => !(message.role === 'assistant' && message.requestId === requestId),
      )
      const existing = previousRemoved.find(
        (message) => message.requestId === requestId && message.role === 'user',
      )
      const withUser = existing
        ? previousRemoved.map((message) => message.id === existing.id
          ? { ...message, status: 'pending' as const }
          : message)
        : [...previousRemoved, {
          id: `user-${requestId}`,
          role: 'user' as const,
          content,
          createdAt: turnCreatedAt,
          requestId,
          status: 'pending' as const,
        }]
      return [...withUser, {
        id: assistantPlaceholderId,
        role: 'assistant',
        content: '',
        createdAt: turnCreatedAt,
        requestId,
        status: 'pending',
        sources: [],
      }]
    })

    try {
      const active = await ensureSession()
      upsertConversation(active, { preview: threadPreview(content) })
      const response = await modoDeskApi.streamMessage(
        active.conversationId,
        requestId,
        content,
        (delta) => {
          if (!receiveSoundPlayed) {
            receiveSoundPlayed = true
            playReceiveSound()
          }
          setMessages((current) => current.map((message) =>
            message.id === assistantPlaceholderId
              ? { ...message, content: `${message.content}${delta}`, status: 'streaming' }
              : message,
          ))
        },
      )
      setMessages((current) => current.map((message) => {
        if (message.role === 'user' && message.requestId === requestId) {
          return { ...message, status: 'sent' as const }
        }
        if (message.id === assistantPlaceholderId) {
          if (!response.assistant_message_id) return null
          return {
            ...message,
            id: response.assistant_message_id,
            content: response.answer,
            createdAt: new Date().toISOString(),
            status: 'sent' as const,
            sources: response.sources,
          }
        }
        return message
      }).filter((message): message is UiMessage => message !== null))
      upsertConversation(active, {
        preview: threadPreview(response.answer || content),
        updatedAt: new Date().toISOString(),
      })
      return true
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The message could not be sent.')
      setMessages((current) => current
        .filter((item) => item.id !== assistantPlaceholderId)
        .map((item) => item.role === 'user' && item.requestId === requestId
          ? { ...item, status: 'failed' as const }
          : item))
      return false
    } finally {
      setIsSending(false)
    }
  }, [ensureSession, isSending, upsertConversation])

  useEffect(() => {
    if (!session) return
    let cancelled = false
    const poll = async () => {
      try {
        const page = await modoDeskApi.history(session.conversationId)
        if (cancelled) return
        const incoming = mapHistory(page.items)
        const nextSequence = Math.max(0, ...incoming.map((item) => item.sequence || 0))
        if (nextSequence > newestSequence.current && incoming.some(
          (item) => (item.sequence || 0) > newestSequence.current && item.role === 'operator',
        )) playReceiveSound()
        newestSequence.current = nextSequence
        setMessages((current) => {
          const pending = current.filter((item) => item.status !== 'sent')
          return [...incoming, ...pending.filter((item) => !incoming.some(
            (stored) => stored.role === item.role && stored.content === item.content,
          ))]
        })
        const last = incoming.at(-1)
        if (last) upsertConversation(session, { preview: threadPreview(last.content) })
      } catch {
        // Foreground sends and explicit restores surface actionable errors.
      }
    }
    const interval = window.setInterval(() => void poll(), 3000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [session, upsertConversation])

  useEffect(() => {
    if (!session) return
    const heartbeat = () => {
      if (document.visibilityState === 'visible') {
        void modoDeskApi.presence(session.conversationId).catch(() => undefined)
      }
    }
    heartbeat()
    const interval = window.setInterval(heartbeat, 25000)
    document.addEventListener('visibilitychange', heartbeat)
    return () => {
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', heartbeat)
    }
  }, [session])

  const retryMessage = useCallback(async (requestId: string) => {
    const failed = messages.find(
      (message) => message.role === 'user' && message.requestId === requestId,
    )
    if (failed) await sendMessage(failed.content, requestId)
  }, [messages, sendMessage])

  const newChat = useCallback(() => {
    if (isSending) return
    restoreVersion.current += 1
    replaceSession(null)
    setMessages([])
    setIsLoadingHistory(false)
    setError(null)
  }, [isSending, replaceSession])

  const selectConversation = useCallback(async (conversationId: string) => {
    if (isSending) return
    const selected = conversations.find((item) => item.conversationId === conversationId)
    if (!selected) return
    replaceSession(selected)
    setMessages([])
    await restoreHistory(selected)
  }, [conversations, isSending, replaceSession, restoreHistory])

  const submitHandoff = useCallback(async (input: HandoffInput) => {
    const active = await ensureSession()
    const response = await modoDeskApi.createHandoff(active.conversationId, input)
    upsertConversation(active, {
      preview: 'Expert request recorded',
      updatedAt: new Date().toISOString(),
    })
    return response.status
  }, [ensureSession, upsertConversation])

  const value = useMemo(() => ({
    messages,
    conversations,
    activeConversationId: session?.conversationId ?? null,
    isSending,
    isLoadingHistory,
    error,
    health,
    sendMessage,
    retryMessage,
    newChat,
    selectConversation,
    refreshHealth,
    submitHandoff,
  }), [
    messages, conversations, session, isSending, isLoadingHistory, error, health,
    sendMessage, retryMessage, newChat, selectConversation, refreshHealth, submitHandoff,
  ])

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChat() {
  const context = useContext(ChatContext)
  if (!context) throw new Error('useChat must be used within ChatProvider')
  return context
}
