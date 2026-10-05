/* oxlint-disable react/set-state-in-effect -- Polling effects synchronize the operator inbox with backend state. */
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import {
  ArrowLeft,
  ArrowUp,
  Bot,
  Check,
  CircleUserRound,
  Clock3,
  LogOut,
  MessageCircleMore,
  Search,
  SlidersHorizontal,
  UserRoundCheck,
  X,
} from 'lucide-react'
import { AdminLogin } from './admin-login'
import { adminApi, supportLabels } from '../../lib/admin-api'
import { cleanMessageContent } from '../../lib/chat-text'
import { isSafeExternalUrl } from '../../lib/utils'
import type {
  AdminConversationDetail,
  AdminConversationSummary,
  AdminSession,
} from '../../types/api'

type InboxFilter = 'all' | 'waiting_for_human' | 'mine' | 'history'
type TimeWindow = '6h' | '12h' | '1d' | '3d' | '7d' | '30d' | 'all'

function initials(value: string) {
  return value.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
}

function relativeTime(value: string) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return 'now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`
  return `${Math.floor(seconds / 86400)}d`
}

function time(value: string) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

function playAlert() {
  try {
    const AudioContextClass = window.AudioContext || (window as typeof window & {
      webkitAudioContext?: typeof AudioContext
    }).webkitAudioContext
    if (!AudioContextClass) return
    const context = new AudioContextClass()
    const oscillator = context.createOscillator()
    const gain = context.createGain()
    oscillator.frequency.setValueAtTime(620, context.currentTime)
    oscillator.frequency.exponentialRampToValueAtTime(880, context.currentTime + 0.12)
    gain.gain.setValueAtTime(0.06, context.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.18)
    oscillator.connect(gain).connect(context.destination)
    oscillator.start()
    oscillator.stop(context.currentTime + 0.18)
  } catch {
    // Audio notifications are a progressive enhancement.
  }
}

export function AdminDashboard() {
  const [session, setSession] = useState<AdminSession | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [conversations, setConversations] = useState<AdminConversationSummary[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<AdminConversationDetail | null>(null)
  const [filter, setFilter] = useState<InboxFilter>('all')
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('1d')
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [reply, setReply] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const previousWaiting = useRef(0)
  const inboxInitialized = useRef(false)

  useEffect(() => {
    adminApi.session()
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setCheckingSession(false))
  }, [])

  const refreshList = useCallback(async (cursor?: string, append = false) => {
    if (!session) return
    try {
      const status = filter === 'waiting_for_human' ? filter : 'all'
      const page = await adminApi.conversations({
        supportStatus: status,
        search,
        scope: filter === 'history' ? 'history' : 'inbox',
        timeWindow,
        cursor,
      })
      const items = filter === 'mine'
        ? page.items.filter((item) => item.assigned_admin === session.display_name)
        : page.items
      const waiting = page.counts.waiting_for_human || 0
      if (inboxInitialized.current && waiting > previousWaiting.current) playAlert()
      previousWaiting.current = waiting
      inboxInitialized.current = true
      setConversations((current) => append
        ? [...current, ...items.filter((item) => !current.some((stored) => stored.id === item.id))]
        : items)
      setNextCursor(page.next_cursor)
      setCounts(page.counts)
      if (!append) {
        setSelectedId((current) => current && items.some((item) => item.id === current)
          ? current
          : items[0]?.id || null)
      }
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load conversations.')
    }
  }, [filter, search, session, timeWindow])

  const refreshDetail = useCallback(async () => {
    if (!selectedId || !session) {
      setDetail(null)
      return
    }
    try {
      setDetail(await adminApi.conversation(selectedId))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load this conversation.')
    }
  }, [selectedId, session])

  useEffect(() => {
    if (!session) return
    void refreshList()
    const interval = window.setInterval(() => void refreshList(), 3000)
    return () => window.clearInterval(interval)
  }, [refreshList, session])

  useEffect(() => {
    void refreshDetail()
    if (!selectedId) return
    const interval = window.setInterval(() => void refreshDetail(), 2200)
    return () => window.clearInterval(interval)
  }, [refreshDetail, selectedId])

  const selected = detail?.conversation
  const inactive = selected?.support_status === 'resolved' || selected?.support_status === 'archived'
  const canTakeover = Boolean(selected && !inactive && (
    selected.support_status === 'waiting_for_human'
    || (selected.support_status === 'ai_active' && selected.visitor_online)
  ))
  const contactEntries = useMemo(
    () => Object.entries(detail?.contact_details || {}).filter(([, value]) => value),
    [detail],
  )

  async function runAction(action: 'takeover' | 'release' | 'resolve') {
    if (!selectedId || busy) return
    setBusy(true)
    setError(null)
    try {
      await adminApi[action](selectedId)
      await Promise.all([refreshList(), refreshDetail()])
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The action could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  async function sendReply(event: FormEvent) {
    event.preventDefault()
    const content = reply.trim()
    if (!selectedId || !content || busy) return
    setBusy(true)
    try {
      await adminApi.reply(selectedId, content)
      setReply('')
      await Promise.all([refreshList(), refreshDetail()])
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The reply could not be sent.')
    } finally {
      setBusy(false)
    }
  }

  async function logout() {
    await adminApi.logout().catch(() => undefined)
    setSession(null)
    setConversations([])
    setDetail(null)
  }

  if (checkingSession) return <div className="admin-loading">Opening operator inbox…</div>
  if (!session) return <AdminLogin onAuthenticated={(displayName) => setSession({ authenticated: true, display_name: displayName })} />

  return (
    <main className="admin-shell">
      <header className="admin-topbar">
        <a href="/" className="admin-brand" aria-label="Return to Modo Studio">
          <img src="/modo-studio-logo.png" alt="Modo Studio" /><i /><strong>Operator Inbox</strong>
        </a>
        <div className="admin-profile">
          <span className="admin-online"><i /> Online</span>
          <span className="admin-avatar">{initials(session.display_name)}</span>
          <span><strong>{session.display_name}</strong><small>Owner</small></span>
          <button type="button" onClick={() => void logout()} aria-label="Sign out"><LogOut /></button>
        </div>
      </header>

      <div className={`admin-workspace ${selectedId ? 'has-selection' : ''}`}>
        <aside className="admin-inbox-panel">
          <div className="admin-panel-heading">
            <h1>Messages</h1>
            <div className="admin-window-filter">
              <SlidersHorizontal aria-hidden="true" />
              <select
                aria-label="Conversation time range"
                value={timeWindow}
                onChange={(event) => setTimeWindow(event.target.value as TimeWindow)}
              >
                <option value="6h">6h</option>
                <option value="12h">12h</option>
                <option value="1d">1d</option>
                <option value="3d">3d</option>
                <option value="7d">7d</option>
                <option value="30d">30d</option>
                <option value="all">All time</option>
              </select>
              <MessageCircleMore aria-hidden="true" />
            </div>
          </div>
          <label className="admin-search">
            <Search aria-hidden="true" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search conversations…" />
            {search && <button type="button" onClick={() => setSearch('')}><X /></button>}
          </label>
          <div className="admin-filters">
            {([
              ['all', `All ${counts.inbox || 0}`],
              ['waiting_for_human', `Waiting ${counts.waiting_for_human || 0}`],
              ['mine', 'Mine'],
              ['history', `History ${counts.history || 0}`],
            ] as const).map(([value, label]) => (
              <button key={value} className={filter === value ? 'active' : ''} onClick={() => setFilter(value)}>{label}</button>
            ))}
          </div>
          <div className="admin-conversation-list">
            {conversations.map((conversation) => (
              <button
                type="button"
                key={conversation.id}
                className={`admin-conversation-row ${selectedId === conversation.id ? 'selected' : ''} ${['resolved', 'archived'].includes(conversation.support_status) ? 'inactive' : ''}`}
                onClick={() => setSelectedId(conversation.id)}
              >
                <span className="admin-list-avatar">{initials(conversation.visitor_name)}</span>
                <span className="admin-list-copy">
                  <strong>{conversation.visitor_name}</strong>
                  <b>{conversation.topic}</b>
                  <small>{conversation.preview}</small>
                </span>
                <span className="admin-row-meta">
                  <time>{relativeTime(conversation.updated_at)}</time>
                  <span className={`admin-presence ${conversation.visitor_online ? 'online' : ''}`}>
                    {conversation.visitor_online ? 'Online' : 'Offline'}
                  </span>
                  <em className={`status-${conversation.support_status}`}>{supportLabels[conversation.support_status]}</em>
                  {conversation.unread_count > 0 && <i>{conversation.unread_count}</i>}
                </span>
              </button>
            ))}
            {nextCursor && (
              <button
                type="button"
                className="admin-load-more"
                onClick={() => void refreshList(nextCursor, true)}
              >
                Load older conversations
              </button>
            )}
            {!conversations.length && <div className="admin-empty">No conversations match this view.</div>}
          </div>
        </aside>

        <section className="admin-thread-panel">
          {selected && detail ? (
            <>
              <header className="admin-thread-header">
                <button className="admin-mobile-back" onClick={() => setSelectedId(null)}><ArrowLeft /></button>
                <span className="admin-thread-avatar">{initials(selected.visitor_name)}</span>
                <div><h2>{selected.visitor_name}</h2><p>{selected.topic}</p></div>
                <span className={`admin-status status-${selected.support_status}`}><i />{supportLabels[selected.support_status]}</span>
              </header>
              <div className="admin-messages">
                {detail.messages.map((message) => {
                  if (message.role === 'system') return (
                    <div className="admin-system-message" key={message.id}>
                      <CircleUserRound /><strong>{message.content}</strong><time>{time(message.created_at)}</time>
                    </div>
                  )
                  const outgoing = message.role === 'assistant' || message.role === 'operator'
                  return (
                    <article key={message.id} className={`admin-message ${outgoing ? 'outgoing' : 'incoming'}`}>
                      <div className="admin-message-meta">
                        <strong>{message.role === 'user' ? selected.visitor_name : message.role === 'operator' ? session.display_name : 'Ren'}</strong>
                        <time>{time(message.created_at)}</time>
                      </div>
                      {outgoing ? (
                        <div className="admin-message-body">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeSanitize]}
                            components={{
                              a: ({ href, children }) => isSafeExternalUrl(href) ? (
                                <a href={href} target="_blank" rel="noreferrer">{children}</a>
                              ) : <span>{children}</span>,
                            }}
                          >
                            {cleanMessageContent(message.content)}
                          </ReactMarkdown>
                        </div>
                      ) : <p>{message.content}</p>}
                    </article>
                  )
                })}
              </div>
              <form className="admin-composer" onSubmit={sendReply}>
                {selected.support_status !== 'human_active' ? (
                  canTakeover ? (
                    <button className="admin-takeover-inline" type="button" onClick={() => void runAction('takeover')} disabled={busy}>
                      <UserRoundCheck /> {selected.support_status === 'waiting_for_human' ? 'Take over conversation' : 'Join conversation'}
                    </button>
                  ) : (
                    <p className="admin-view-only">
                      {inactive ? 'This conversation is view-only.' : 'The visitor is offline. You can review this thread, but cannot take it over.'}
                    </p>
                  )
                ) : (
                  <>
                    <textarea value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Reply as Modo Studio" rows={2} />
                    <button type="submit" disabled={!reply.trim() || busy} aria-label="Send reply"><ArrowUp /></button>
                  </>
                )}
              </form>
            </>
          ) : (
            <div className="admin-thread-empty"><MessageCircleMore /><h2>Select a conversation</h2><p>Choose a thread to review messages or take over from Ren.</p></div>
          )}
        </section>

        <aside className="admin-details-panel">
          {selected && detail ? (
            <>
              <section className="admin-detail-card">
                <h3>Visitor details</h3>
                <div className="admin-visitor"><span>{initials(selected.visitor_name)}</span><div><strong>{selected.visitor_name}</strong><small>{contactEntries.find(([key]) => key === 'email')?.[1] || 'Anonymous visitor'}</small></div></div>
                <dl>
                  {contactEntries.filter(([key]) => key !== 'email').map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{value}</dd></div>)}
                  <div><dt>First seen</dt><dd>{relativeTime(selected.created_at)} ago</dd></div>
                  <div><dt>Messages</dt><dd>{selected.message_count}</dd></div>
                  <div><dt>Presence</dt><dd>{selected.visitor_online ? 'Online now' : 'Offline'}</dd></div>
                  <div><dt>Last seen</dt><dd>{selected.visitor_last_seen_at ? `${relativeTime(selected.visitor_last_seen_at)} ago` : 'Not recorded'}</dd></div>
                </dl>
              </section>
              <section className="admin-detail-card admin-status-card">
                <h3>Conversation status</h3>
                <p className={`admin-detail-status status-${selected.support_status}`}><i />{supportLabels[selected.support_status]}</p>
                <dl>
                  <div><dt>Assigned to</dt><dd>{selected.assigned_admin || 'Unassigned'}</dd></div>
                  <div><dt>Started</dt><dd>{relativeTime(selected.created_at)} ago</dd></div>
                  <div><dt>Request</dt><dd>{detail.handoff_reason || 'No human request'}</dd></div>
                </dl>
                {selected.support_status !== 'human_active' ? (
                  canTakeover ? (
                    <button className="admin-primary-action" onClick={() => void runAction('takeover')} disabled={busy}><UserRoundCheck /> Take over</button>
                  ) : (
                    <p className="admin-detail-note">{inactive ? 'Archived and resolved threads are view-only.' : 'Takeover becomes available when this visitor returns.'}</p>
                  )
                ) : (
                  <button className="admin-secondary-action" onClick={() => void runAction('release')} disabled={busy}><Bot /> Return to Ren</button>
                )}
                {!inactive && <button className="admin-resolve-action" onClick={() => void runAction('resolve')} disabled={busy}><Check /> Resolve</button>}
              </section>
            </>
          ) : null}
        </aside>
      </div>
      {error && <div className="admin-error"><Clock3 />{error}<button onClick={() => setError(null)}><X /></button></div>}
    </main>
  )
}
