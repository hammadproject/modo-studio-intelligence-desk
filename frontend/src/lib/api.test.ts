import { afterEach, describe, expect, it, vi } from 'vitest'
import { modoDeskApi } from './api'

afterEach(() => vi.restoreAllMocks())

describe('modoDeskApi', () => {
  it('creates an anonymous conversation without exposing an admin key', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      conversation_id: 'conversation-1',
      access_token: 'conversation-token',
      created_at: '2026-10-02T00:00:00Z',
    }), { status: 201, headers: { 'Content-Type': 'application/json' } }))

    await expect(modoDeskApi.createConversation()).resolves.toMatchObject({
      conversation_id: 'conversation-1',
    })
    const [, options] = fetchMock.mock.calls[0]
    expect(options?.method).toBe('POST')
    expect(new Headers(options?.headers).has('x-admin-key')).toBe(false)
  })

  it('uses the HttpOnly visitor session and stable request id for messages', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      conversation_id: 'conversation-1', request_id: 'request-1', assistant_message_id: 'message-2',
      answer: 'A website project starts at $5,000.', route: 'knowledge', sources: [],
      handoff_status: null, provider_mode: 'live',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await modoDeskApi.sendMessage('conversation-1', 'request-1', 'How much?')
    const [, options] = fetchMock.mock.calls[0]
    expect(options?.credentials).toBe('include')
    expect(new Headers(options?.headers).has('Authorization')).toBe(false)
    expect(JSON.parse(String(options?.body))).toEqual({ request_id: 'request-1', message: 'How much?' })
  })

  it('surfaces the backend error contract', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      error: { code: 'invalid_token', message: 'Conversation token is invalid.' },
    }), { status: 401, headers: { 'Content-Type': 'application/json' } }))

    await expect(modoDeskApi.history('conversation-1')).rejects.toEqual(
      expect.objectContaining({
        status: 401,
        code: 'invalid_token',
        message: 'Conversation token is invalid.',
      }),
    )
  })

  it('streams assistant deltas and returns the completed response', async () => {
    const completed = {
      conversation_id: 'conversation-1', request_id: 'request-1', assistant_message_id: 'message-2',
      answer: 'A streamed answer.', route: 'knowledge', sources: [], handoff_status: null,
      provider_mode: 'live',
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response([
      'event: status\ndata: {"status":"thinking"}\n\n',
      'event: delta\ndata: {"delta":"A streamed "}\n\n',
      'event: delta\ndata: {"delta":"answer."}\n\n',
      `event: complete\ndata: ${JSON.stringify({ response: completed })}\n\n`,
    ].join(''), { status: 200, headers: { 'Content-Type': 'text/event-stream' } }))
    const deltas: string[] = []

    await expect(modoDeskApi.streamMessage(
      'conversation-1', 'request-1', 'Question',
      (delta) => deltas.push(delta),
    )).resolves.toEqual(completed)
    expect(deltas).toEqual(['A streamed ', 'answer.'])
  })
})
