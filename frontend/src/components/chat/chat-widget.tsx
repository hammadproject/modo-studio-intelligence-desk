import { ChevronLeft, History, MessageCircle, Plus, UserRound, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { suggestedQuestions } from '../../data/content'
import { useChat } from '../../hooks/use-chat'
import { AssistantGreeting } from './assistant-greeting'
import { ChatComposer } from './chat-composer'
import { ConversationHistory } from './conversation-history'
import { MessageList } from './message-list'

const NUDGE_DISMISSED_KEY = 'modo.chat.nudge.dismissed'

function wasNudgeDismissed() {
  try {
    return sessionStorage.getItem(NUDGE_DISMISSED_KEY) === 'true'
  } catch {
    return false
  }
}

export function ChatWidget({ onExpert }: { onExpert: () => void }) {
  const [open, setOpen] = useState(false)
  const [nudgeDismissed, setNudgeDismissed] = useState(wasNudgeDismissed)
  const [showNudge, setShowNudge] = useState(false)
  const [view, setView] = useState<'chat' | 'history'>('chat')
  const {
    messages,
    conversations,
    activeConversationId,
    isSending,
    isLoadingHistory,
    error,
    health,
    sendMessage,
    retryMessage,
    newChat,
    selectConversation,
    refreshHealth,
  } = useChat()

  useEffect(() => {
    if (open) void refreshHealth()
  }, [open, refreshHealth])

  useEffect(() => {
    if (open || nudgeDismissed) return
    const timer = window.setTimeout(() => setShowNudge(true), 8_000)
    return () => window.clearTimeout(timer)
  }, [open, nudgeDismissed])

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    if (open) window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open])

  const available = health?.status === 'ready' || health?.status === 'degraded'

  function dismissNudge() {
    setShowNudge(false)
    setNudgeDismissed(true)
    try {
      sessionStorage.setItem(NUDGE_DISMISSED_KEY, 'true')
    } catch {
      // The prompt can still be dismissed when browser storage is unavailable.
    }
  }

  function openChat() {
    dismissNudge()
    setOpen(true)
  }

  function startNewChat() {
    newChat()
    setView('chat')
  }

  async function openConversation(conversationId: string) {
    await selectConversation(conversationId)
    setView('chat')
  }

  return (
    <div className="chat-shell">
      {open && (
        <section className="chat-panel" aria-label="Ren, Modo Studio AI assistant">
          <header className="chat-header">
            <div>
              <strong>{view === 'history' ? 'Messages' : 'Ren · Modo Studio'}</strong>
              {view === 'history' ? (
                <span className="history-count">{conversations.length} saved {conversations.length === 1 ? 'chat' : 'chats'}</span>
              ) : (
                <span className={available ? 'status-online' : 'status-offline'}>
                  <i /> {available ? 'Assistant available' : 'Service unavailable'}
                </span>
              )}
            </div>
            <div className="chat-header-actions">
              {view === 'chat' ? (
                <button type="button" onClick={() => setView('history')} aria-label="View conversation history" title="Messages" disabled={isSending}>
                  <History aria-hidden="true" />
                </button>
              ) : (
                <button type="button" onClick={() => setView('chat')} aria-label="Return to current chat" title="Back to chat">
                  <ChevronLeft aria-hidden="true" />
                </button>
              )}
              <button type="button" onClick={startNewChat} aria-label="Start a new chat" title="New chat" disabled={isSending}>
                <Plus aria-hidden="true" />
              </button>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close chat">
                <X aria-hidden="true" />
              </button>
            </div>
          </header>

          <div className={view === 'history' ? 'chat-body chat-body-history' : 'chat-body'}>
            {view === 'history' ? (
              <ConversationHistory
                conversations={conversations}
                activeConversationId={activeConversationId}
                disabled={isSending}
                onSelect={(conversationId) => void openConversation(conversationId)}
                onNew={startNewChat}
              />
            ) : messages.length === 0 && !isLoadingHistory ? (
              <div className="chat-welcome">
                <AssistantGreeting />
                <p className="suggestion-label">Choose a question or write your own:</p>
                <div className="suggested-questions">
                  {suggestedQuestions.map((question) => (
                    <button key={question} type="button" onClick={() => void sendMessage(question)} disabled={isSending}>
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <MessageList
                messages={messages}
                isLoading={isLoadingHistory}
                onRetry={(requestId) => void retryMessage(requestId)}
              />
            )}
            {view === 'chat' && error && <div className="chat-error" role="alert">{error}</div>}
          </div>

          {view === 'chat' && <div className="chat-footer">
            <button type="button" className="chat-expert" onClick={onExpert}>
              <UserRound aria-hidden="true" /> Record an expert request
            </button>
            <ChatComposer disabled={isSending || !available} onSend={sendMessage} />
          </div>}
        </section>
      )}

      {!open && showNudge && (
        <aside className="chat-nudge" aria-label="Message from Ren" aria-live="polite">
          <button type="button" className="chat-nudge-main" onClick={openChat}>
            <span className="nudge-mark" aria-hidden="true">
              <img src="/modo-studio-logo.png" alt="" />
            </span>
            <span>
              <strong>Hi there <span aria-hidden="true">👋</span></strong>
              <span>You’re speaking with Ren. How can I help you today?</span>
              <small>Ren · AI assistant</small>
            </span>
          </button>
          <button type="button" className="chat-nudge-close" onClick={dismissNudge} aria-label="Dismiss Ren’s message">
            <X aria-hidden="true" />
          </button>
        </aside>
      )}

      <button
        type="button"
        className="chat-launcher"
        onClick={() => open ? setOpen(false) : openChat()}
        aria-label={open ? 'Close Ren, Modo Studio AI assistant' : 'Open Ren, Modo Studio AI assistant'}
        aria-expanded={open}
      >
        {open ? <X aria-hidden="true" /> : <MessageCircle aria-hidden="true" />}
      </button>
    </div>
  )
}
