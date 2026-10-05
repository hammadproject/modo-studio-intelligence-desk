import { MessageSquareText } from 'lucide-react'
import type { ConversationSummary } from '../../hooks/use-chat'
import { plainTextPreview } from '../../lib/chat-text'

function relativeTime(value: string) {
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime())
  const minutes = Math.floor(elapsed / 60_000)
  if (minutes < 1) return 'Now'
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return days < 7 ? `${days}d` : new Date(value).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric',
  })
}

export function ConversationHistory({
  conversations,
  activeConversationId,
  disabled,
  onSelect,
  onNew,
}: {
  conversations: ConversationSummary[]
  activeConversationId: string | null
  disabled: boolean
  onSelect: (conversationId: string) => void
  onNew: () => void
}) {
  return (
    <div className="conversation-history">
      <div className="conversation-list" aria-label="Previous conversations">
        {conversations.length ? conversations.map((conversation) => (
          <button
            key={conversation.conversationId}
            type="button"
            className={conversation.conversationId === activeConversationId ? 'conversation-item active' : 'conversation-item'}
            onClick={() => onSelect(conversation.conversationId)}
            disabled={disabled}
          >
            <span className="conversation-icon" aria-hidden="true">
              <img src="/modo-studio-logo.png" alt="" />
            </span>
            <span className="conversation-copy">
              <strong>Ren</strong>
              <span>{plainTextPreview(conversation.preview)}</span>
            </span>
            <time dateTime={conversation.updatedAt}>{relativeTime(conversation.updatedAt)}</time>
          </button>
        )) : (
          <div className="conversation-empty">
            <MessageSquareText aria-hidden="true" />
            <strong>No previous conversations yet</strong>
            <span>Your chats with Ren will appear here.</span>
          </div>
        )}
      </div>
      <button type="button" className="history-new-chat" onClick={onNew} disabled={disabled}>
        Ask a question
      </button>
    </div>
  )
}
