import { useState, type FormEvent } from 'react'
import { ArrowRight, LockKeyhole } from 'lucide-react'
import { adminApi } from '../../lib/admin-api'

export function AdminLogin({ onAuthenticated }: { onAuthenticated: (name: string) => void }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!key.trim() || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const session = await adminApi.login(key)
      setKey('')
      onAuthenticated(session.display_name)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sign-in failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="admin-login-shell">
      <section className="admin-login-card">
        <img src="/modo-studio-logo.png" alt="Modo Studio" />
        <p className="admin-kicker">Private workspace</p>
        <h1>Operator<br /><em>Inbox.</em></h1>
        <p>Monitor Ren’s conversations and step in when a visitor needs the studio team.</p>
        <form onSubmit={submit}>
          <label htmlFor="admin-key">Admin key</label>
          <div className="admin-key-field">
            <LockKeyhole aria-hidden="true" />
            <input
              id="admin-key"
              type="password"
              value={key}
              onChange={(event) => setKey(event.target.value)}
              autoComplete="current-password"
              placeholder="Enter your private key"
              autoFocus
            />
            <button type="submit" disabled={submitting} aria-label="Open operator inbox">
              <ArrowRight aria-hidden="true" />
            </button>
          </div>
          {error && <p className="admin-login-error">{error}</p>}
        </form>
      </section>
    </main>
  )
}
