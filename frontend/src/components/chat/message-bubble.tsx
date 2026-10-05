import { RotateCcw } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import type { UiMessage } from '../../hooks/use-chat'
import { formatMessageTime } from '../../lib/chat-time'
import { isSafeExternalUrl } from '../../lib/utils'

function cleanSourceMarkers(content: string) {
  return content
    .replace(/【\s*sources?\s*:[^】]+】/gi, '')
    .replace(/\[\s*sources?\s*:\s*[^\]]+\]/gi, '')
    .replace(/\s+([.,;!?])/g, '$1')
}

export function MessageBubble({
  message,
  now,
  onRetry,
}: {
  message: UiMessage
  now?: number
  onRetry: (requestId: string) => void
}) {
  const isUser = message.role === 'user'
  if (message.role === 'system') {
    return (
      <div className="chat-system-event" role="status">
        <span>{message.content}</span>
        {message.status === 'sent' && (
          <time dateTime={message.createdAt}>{formatMessageTime(message.createdAt, now)}</time>
        )}
      </div>
    )
  }
  return (
    <article className={`message-row ${isUser ? 'message-row-user' : 'message-row-assistant'}`}>
      <div className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
        {!isUser && message.status === 'pending' && !message.content ? (
          <div className="typing-indicator" role="status" aria-label="Ren is thinking">
            <span /><span /><span />
          </div>
        ) : isUser ? (
          <p>{message.content}</p>
        ) : (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSanitize]}
              components={{
                a: ({ href, children }) => isSafeExternalUrl(href) ? (
                  <a href={href} target="_blank" rel="noreferrer">{children}</a>
                ) : <span>{children}</span>,
              }}
            >
              {cleanSourceMarkers(message.content)}
            </ReactMarkdown>
            {message.role === 'operator' && <span className="operator-byline">Modo Studio team</span>}
            {message.status === 'streaming' && (
              <span className="streaming-cursor" aria-hidden="true" />
            )}
          </>
        )}
        {isUser && message.status === 'pending' && <span className="message-status">Sending…</span>}
        {message.status === 'failed' && message.requestId && (
          <button type="button" className="message-retry" onClick={() => onRetry(message.requestId!)}>
            <RotateCcw aria-hidden="true" /> Retry
          </button>
        )}
      </div>
      {message.status === 'sent' && (
        <time className="message-time" dateTime={message.createdAt}>
          {formatMessageTime(message.createdAt, now)}
        </time>
      )}
    </article>
  )
}
