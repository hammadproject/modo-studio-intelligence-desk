export type ProviderMode = 'live' | 'deterministic'
export type ChatRoute = 'knowledge' | 'general' | 'clarification' | 'handoff' | 'action' | 'off_topic' | 'human'

export interface ConversationCreated {
  conversation_id: string
  access_token: string | null
  created_at: string
}

export interface VisitorConversationSummary {
  conversation_id: string
  preview: string
  support_status: SupportStatus
  created_at: string
  updated_at: string
}

export interface VisitorConversationPage {
  items: VisitorConversationSummary[]
}

export interface SourceCitation {
  chunk_id: string
  document_id: string
  title: string
  source: string
  source_url: string | null
  relevance_score: number
}

export interface ChatOutput {
  conversation_id: string
  request_id: string
  assistant_message_id: string | null
  answer: string
  route: ChatRoute
  sources: SourceCitation[]
  handoff_status: string | null
  provider_mode: ProviderMode
}

export interface HistoryMessage {
  id: string
  sequence: number
  role: string
  content: string
  created_at: string
  metadata: {
    route?: ChatRoute
    sources?: SourceCitation[]
    handoff_status?: string | null
    provider_mode?: ProviderMode
  }
}

export interface MessagePage {
  items: HistoryMessage[]
  next_after_sequence: number | null
}

export interface HandoffInput {
  reason: string
  contact_details: Record<string, string> | null
}

export interface HandoffOutput {
  id: string
  conversation_id: string
  status: 'recorded'
  reason: string
  created_at: string
}

export interface ReadinessOutput {
  status: 'ready' | 'degraded' | 'not_ready'
  database: string
  providers: string
  knowledge_base: 'available' | 'empty' | 'unavailable'
  provider_mode: string
}

export interface ApiErrorPayload {
  error?: {
    code?: string
    message?: string
    details?: unknown
    request_id?: string | null
  }
}

export type SupportStatus = 'ai_active' | 'waiting_for_human' | 'human_active' | 'resolved' | 'archived'

export interface AdminSession {
  authenticated: boolean
  display_name: string
}

export interface AdminConversationSummary {
  id: string
  visitor_name: string
  topic: string
  preview: string
  support_status: SupportStatus
  assigned_admin: string | null
  unread_count: number
  message_count: number
  created_at: string
  updated_at: string
  human_requested_at: string | null
  visitor_last_seen_at: string | null
  visitor_online: boolean
}

export interface AdminConversationPage {
  items: AdminConversationSummary[]
  counts: Record<string, number>
  next_cursor: string | null
}

export interface AdminConversationDetail {
  conversation: AdminConversationSummary
  messages: HistoryMessage[]
  contact_details: Record<string, string> | null
  handoff_reason: string | null
}
