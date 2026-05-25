'use client'
import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'

// Password-recovery landing. The recovery email links to
// /auth/confirm?...&type=recovery&next=/account/update-password — that route
// verifies the token (establishing a short-lived session) and redirects here,
// where the user sets a new password.
export default function UpdatePasswordPage() {
  const { updatePassword, user, loading, configured } = useAuth()
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 8) return setError('Use at least 8 characters.')
    if (password !== confirm) return setError('Passwords do not match.')
    setBusy(true)
    const { error } = await updatePassword(password)
    setBusy(false)
    if (error) return setError(error)
    setDone(true)
    setTimeout(() => router.push('/account'), 1600)
  }

  return (
    <main style={{ minHeight: '100dvh', background: 'var(--d-bg)', display: 'grid', placeItems: 'center', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 400, background: 'rgba(5,26,19,0.6)', border: '0.5px solid var(--hero-line)', borderRadius: 16, padding: '28px 26px' }}>
        <a href="/" style={{ fontFamily: 'var(--display)', fontSize: 20, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--hero-ink)', textDecoration: 'none' }}>
          eamos
        </a>
        <h1 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 19, color: 'var(--hero-ink)', margin: '18px 0 6px' }}>
          Set a new password
        </h1>

        {loading ? (
          <p style={muted}>Checking your link…</p>
        ) : !configured ? (
          <p style={muted}>Auth isn’t configured in this environment.</p>
        ) : !user ? (
          <>
            <p style={muted}>This reset link is invalid or has expired. Request a new one from the sign-in panel.</p>
            <a href="/account" style={{ ...primaryBtn, display: 'block', textAlign: 'center', textDecoration: 'none', marginTop: 16 }}>
              Back to sign in
            </a>
          </>
        ) : done ? (
          <p style={{ ...muted, color: 'var(--em-bright)' }}>Password updated — taking you to your account…</p>
        ) : (
          <form onSubmit={onSubmit} className="flex flex-col gap-3" style={{ marginTop: 14 }}>
            <p style={{ ...muted, margin: '0 0 4px' }}>Signed in as {user.email}. Choose a new password below.</p>
            <label className="flex flex-col gap-1.5">
              <span style={label}>New password</span>
              <input data-tone="dark" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" placeholder="••••••••" style={inputStyle} />
            </label>
            <label className="flex flex-col gap-1.5">
              <span style={label}>Confirm new password</span>
              <input data-tone="dark" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" placeholder="••••••••" style={inputStyle} />
            </label>
            {error && <p style={errorBox} role="alert">{error}</p>}
            <button type="submit" disabled={busy} style={{ ...primaryBtn, opacity: busy ? 0.7 : 1, marginTop: 4 }}>
              {busy ? 'Updating…' : 'Update password'}
            </button>
          </form>
        )}
      </div>
    </main>
  )
}

const muted: React.CSSProperties = { fontSize: 13.5, lineHeight: 1.6, color: 'var(--hero-ink-2)', margin: '8px 0 0' }
const label: React.CSSProperties = { fontSize: 11.5, fontWeight: 600, color: 'var(--hero-ink-2)' }
const inputStyle: React.CSSProperties = {
  width: '100%', height: 40, padding: '0 12px', borderRadius: 10,
  background: 'var(--hero-glass)', border: '0.5px solid var(--hero-line)',
  color: 'var(--hero-ink)', fontSize: 13.5, outline: 'none',
}
const primaryBtn: React.CSSProperties = {
  height: 40, borderRadius: 10, border: 'none', background: 'var(--em)',
  color: '#04140e', fontSize: 13, fontWeight: 600, cursor: 'pointer',
}
const errorBox: React.CSSProperties = {
  margin: 0, padding: '8px 11px', borderRadius: 8,
  background: 'rgba(220,80,70,0.14)', border: '0.5px solid rgba(220,80,70,0.4)',
  color: '#fca5a5', fontSize: 12, lineHeight: 1.45,
}
