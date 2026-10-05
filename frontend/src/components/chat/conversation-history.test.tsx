import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ConversationHistory } from './conversation-history'

describe('ConversationHistory', () => {
  it('lists saved conversations and restores the selected thread', () => {
    const onSelect = vi.fn()
    render(
      <ConversationHistory
        conversations={[{
          conversationId: 'conversation-1',
          title: 'Visual identity timeline',
          preview: '**A combined engagement takes 5–7 weeks.**',
          updatedAt: new Date().toISOString(),
        }]}
        activeConversationId={null}
        disabled={false}
        onSelect={onSelect}
        onNew={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /Ren/i }))
    expect(onSelect).toHaveBeenCalledWith('conversation-1')
    expect(screen.getByText('A combined engagement takes 5–7 weeks.')).toBeInTheDocument()
    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument()
    expect(screen.queryByText('secret-token')).not.toBeInTheDocument()
  })
})
