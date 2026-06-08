'use client'
import Link from 'next/link'
import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { Field, AuthPanelStyles } from '@/components/auth/AuthPanel'

// Password-recovery landing. The recovery email links to
// /auth/confirm?...&type=recovery&next=/account/update-password — that route
// verifies the token (establishing a short-lived session) and redirects here.
// Composes the shared AuthPanel Field (password reveal toggle + one field idiom)
// instead of a standalone .upw-* system.
export default function UpdatePasswordPage() {
  const { updatePassword, user, loading, configured } = useAuth()
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ password?: string; confirm?: string }>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const setFieldError = (field: 'password' | 'confirm', msg: string) =>
    setFieldErrors((prev) => ({ ...prev, [field]: msg }))
  const clearFieldError = (field: 'password' | 'confirm') =>
    setFieldErrors((prev) => { const n = { ...prev }; delete n[field]; return n })

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (busy) return
    setError(null)
    // Field-scoped rules surface under their field (one wording, one place).
    if (password.length < 8) {
      setFieldError('password', 'Use at least 8 characters.')
      return
    }
    if (password !== confirm) {
      setFieldError('confirm', 'Passwords do not match.')
      return
    }
    setBusy(true)
    const { error } = await updatePassword(password)
    setBusy(false)
    if (error) return setError(error)
    setDone(true)
    setTimeout(() => router.push('/account'), 1600)
  }

  return (
    <>
      <AuthPanelStyles />
      <main
        style={{
          minHeight: '100dvh',
          background: 'var(--bg-soft)',
          display: 'grid',
          placeItems: 'center',
          padding: 24,
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 400,
            background: 'var(--bg)',
            border: '0.5px solid var(--line)',
            borderRadius: 'var(--r-lg)',
            padding: '28px 26px',
            boxShadow: 'var(--elev-2)',
          }}
        >
          <Link
            href="/"
            style={{
              fontFamily: 'var(--display)',
              fontSize: 19,
              fontWeight: 400,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
              textDecoration: 'none',
            }}
          >
            Eamos
          </Link>
          <h1
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 20,
              color: 'var(--ink)',
              margin: '18px 0 6px',
              letterSpacing: '-0.01em',
            }}
          >
            Set a new password
          </h1>

          {loading ? (
            <p style={muted}>Checking your link…</p>
          ) : !configured ? (
            <p style={muted}>Auth is not configured in this environment.</p>
          ) : !user ? (
            <>
              <p style={muted}>
                This reset link is invalid or has expired. Request a new one from the sign-in panel.
              </p>
              <Link
                href="/account"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textDecoration: 'none',
                  marginTop: 16,
                  height: 40,
                  borderRadius: 'var(--r-md)',
                  background: 'var(--teal)',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 600,
                }}
              >
                Back to sign in
              </Link>
            </>
          ) : done ? (
            <p
              style={{ ...muted, color: 'var(--teal-deep)' }}
              role="status"
              aria-live="polite"
            >
              Password updated — taking you to your account…
            </p>
          ) : (
            <form onSubmit={onSubmit} className="flex flex-col gap-3" style={{ marginTop: 14 }}>
              <p style={{ ...muted, margin: '0 0 4px' }}>
                Signed in as{' '}
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{user.email}</span>.
                Choose a new password.
              </p>
              <Field
                label="New password"
                type="password"
                value={password}
                onChange={setPassword}
                autoComplete="new-password"
                placeholder="••••••••"
                dark={false}
                fieldError={fieldErrors.password}
                onBlur={() => {
                  if (password && password.length < 8)
                    setFieldError('password', 'Use at least 8 characters.')
                  else clearFieldError('password')
                }}
              />
              <Field
                label="Confirm new password"
                type="password"
                value={confirm}
                onChange={setConfirm}
                autoComplete="new-password"
                placeholder="••••••••"
                dark={false}
                fieldError={fieldErrors.confirm}
                onBlur={() => {
                  if (confirm && confirm !== password)
                    setFieldError('confirm', 'Passwords do not match.')
                  else clearFieldError('confirm')
                }}
              />
              {error && (
                <p
                  style={{
                    margin: 0,
                    padding: '8px 11px',
                    borderRadius: 8,
                    background: 'var(--err-tint)',
                    border: '0.5px solid rgba(184,43,43,0.3)',
                    color: 'var(--err)',
                    fontSize: 12,
                    lineHeight: 1.45,
                  }}
                  role="alert"
                >
                  {error}
                </p>
              )}
              <button
                type="submit"
                disabled={busy}
                aria-busy={busy}
                className="ap-primary-btn"
                style={{ marginTop: 4, width: '100%' }}
              >
                {busy ? 'Updating…' : 'Update password'}
              </button>
            </form>
          )}
        </div>
      </main>
    </>
  )
}

const muted: React.CSSProperties = {
  fontSize: 13.5,
  lineHeight: 1.6,
  color: 'var(--ink-3)',
  margin: '8px 0 0',
}
