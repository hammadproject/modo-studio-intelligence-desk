import { describe, expect, it } from 'vitest'
import { formatConversationDate, formatMessageTime, ONE_DAY } from './chat-time'

describe('chat time formatting', () => {
  it('shows Just now for messages less than one minute old', () => {
    const now = Date.parse('2026-10-02T18:06:30.000Z')
    expect(formatMessageTime('2026-10-02T18:06:00.000Z', now)).toBe('Just now')
  })

  it('formats older messages as a local clock time', () => {
    const timestamp = '2026-10-02T18:06:00.000Z'
    expect(formatMessageTime(timestamp, Date.parse(timestamp) + ONE_DAY)).toMatch(/\d{1,2}:06\s[AP]M/)
  })

  it('formats the restored conversation marker with date and time', () => {
    expect(formatConversationDate('2026-10-01T17:25:00.000Z')).toMatch(/October 1 at \d{1,2}:25\s[AP]M/)
  })
})
