const ONE_MINUTE = 60_000
export const ONE_DAY = 24 * 60 * ONE_MINUTE

export function formatMessageTime(value: string, now = Date.now()) {
  const timestamp = new Date(value).getTime()
  if (!Number.isFinite(timestamp)) return ''
  if (Math.max(0, now - timestamp) < ONE_MINUTE) return 'Just now'
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(timestamp)
}

export function formatConversationDate(value: string) {
  const timestamp = new Date(value).getTime()
  if (!Number.isFinite(timestamp)) return ''
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(timestamp)
}
