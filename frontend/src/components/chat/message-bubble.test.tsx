import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { UiMessage } from '../../hooks/use-chat'
import { MessageBubble } from './message-bubble'

const assistantMessage: UiMessage = {
  id: 'assistant-1',
  role: 'assistant',
  content: 'See [our process](https://example.com/process). 【source:chunk-1】 [ source:chunk-2 ] [Sources: chunk-3; chunk-4]',
  createdAt: '2026-10-02T18:06:00.000Z',
  status: 'sent',
  sources: [{
    chunk_id: 'chunk-1', document_id: 'document-1', title: 'Studio guide', source: 'markdown',
    source_url: 'https://example.com/guide', relevance_score: 0.9,
  }],
}

describe('MessageBubble', () => {
  it('renders safe markdown and removes internal source markers', () => {
    render(<MessageBubble message={assistantMessage} onRetry={vi.fn()} />)
    expect(screen.getByRole('link', { name: 'our process' })).toHaveAttribute('target', '_blank')
    expect(screen.queryByText(/source:chunk-1/)).not.toBeInTheDocument()
    expect(screen.queryByText(/source:chunk-2/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Sources: chunk-3/)).not.toBeInTheDocument()
    expect(screen.queryByText('Sources')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Studio guide' })).not.toBeInTheDocument()
  })

  it('does not create links for unsafe protocols', () => {
    render(<MessageBubble message={{
      ...assistantMessage,
      content: '[unsafe](javascript:alert(1))',
      sources: [],
    }} onRetry={vi.fn()} />)
    expect(screen.queryByRole('link', { name: 'unsafe' })).not.toBeInTheDocument()
    expect(screen.getByText('unsafe')).toBeInTheDocument()
  })
})
