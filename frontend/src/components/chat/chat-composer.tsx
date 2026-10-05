import { ArrowUp } from 'lucide-react'
import { useState, type FormEvent, type KeyboardEvent } from 'react'

export function ChatComposer({
  disabled,
  onSend,
}: {
  disabled: boolean
  onSend: (value: string) => Promise<boolean>
}) {
  const [value, setValue] = useState('')

  async function submit() {
    if (!value.trim() || disabled) return
    const sent = await onSend(value)
    if (sent) setValue('')
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void submit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submit()
    }
  }

  return (
    <form className="chat-composer" onSubmit={handleSubmit}>
      <label htmlFor="chat-message" className="sr-only">Message Ren, Modo Studio AI assistant</label>
      <textarea
        id="chat-message"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about services, pricing, or process…"
        rows={1}
        maxLength={1500}
        disabled={disabled}
      />
      <button type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
        <ArrowUp aria-hidden="true" />
      </button>
    </form>
  )
}
