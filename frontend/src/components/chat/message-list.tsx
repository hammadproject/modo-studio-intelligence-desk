import { useEffect, useMemo, useRef, useState } from 'react'
import type { UiMessage } from '../../hooks/use-chat'
import { formatConversationDate, ONE_DAY } from '../../lib/chat-time'
import { AssistantGreeting } from './assistant-greeting'
import { MessageBubble } from './message-bubble'

export function MessageList({
  messages,
  isLoading,
  onRetry,
}: {
  messages: UiMessage[]
  isLoading: boolean
  onRetry: (requestId: string) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const nearBottom = useRef(true)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30_000)
    return () => window.clearInterval(timer)
  }, [])

  const conversationDate = useMemo(() => {
    const firstMessage = messages[0]
    if (!firstMessage) return null
    const startedAt = new Date(firstMessage.createdAt).getTime()
    if (!Number.isFinite(startedAt) || now - startedAt < ONE_DAY) return null
    return formatConversationDate(firstMessage.createdAt)
  }, [messages, now])

  useEffect(() => {
    if (nearBottom.current) {
      const container = containerRef.current
      if (container) container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
    }
  }, [messages])

  if (isLoading) {
    return <div className="chat-loading" role="status">Restoring your conversation…</div>
  }

  return (
    <div
      ref={containerRef}
      className="message-list"
      onScroll={(event) => {
        const element = event.currentTarget
        nearBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < 80
      }}
    >
      <AssistantGreeting />
      {conversationDate && (
        <div className="conversation-date" role="separator">{conversationDate}</div>
      )}
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} now={now} onRetry={onRetry} />
      ))}
      <div className="sr-only" aria-live="polite">
        {messages.at(-1)?.role === 'assistant' ? 'Modo Studio Assistant replied.' : ''}
      </div>
    </div>
  )
}
