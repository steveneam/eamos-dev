'use client'
import Link from 'next/link'
import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'

// Password-recovery landing. The recovery email links to
// /auth/confirm?...&type=recovery&next=/account/update-password — that route
// verifies the token (establishing a short-lived session) and redirects here.
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
    <>
      <style>{`
        .upw-field {
          width: 100%;
          height: 40px;
          padding: 0 12px;
          border-radius: var(--r-md);
          background: var(--bg-soft);
          border: 0.5px solid var(--line-2);
          color: var(--ink);
          font-size: 13.5px;
          outline: none;
          transition: border-color var(--dur-1) var(--ease-standard),
                      box-shadow var(--dur-1) var(--ease-standard);
        }
        /* Hover: same teal-axis signal as the rest of the brand surface. */
        .upw-field:hover:not(:focus):not([aria-invalid="true"]) {
          border-color: var(--teal);
        }
        .upw-field:focus-visible,
        .upw-field:focus {
          border-color: var(--teal);
          box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
          outline: none;
        }
        .upw-field[aria-invalid="true"] {
          border-color: var(--err);
        }
        .upw-field[aria-invalid="true"]:focus-visible,
        .upw-field[aria-invalid="true"]:focus {
          border-color: var(--err);
          box-shadow: 0 0 0 3px rgba(184,43,43,0.10);
        }
        .upw-submit {
          height: 40px;
          width: 100%;
          border-radius: var(--r-md);
          border: none;
          background: var(--teal);
          color: #fff;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: background var(--dur-1) var(--ease-standard),
                      box-shadow var(--dur-1) var(--ease-standard),
                      transform var(--dur-1) var(--ease-standard);
        }
        .upw-submit:hover:not(:disabled) { background: var(--teal-deep); }
        .upw-submit:active:not(:disabled) { transform: translateY(1px); }
        .upw-submit:focus-visible {
          outline: none;
          box-shadow: 0 0 0 3px rgba(29,158,117,0.25);
        }
        .upw-submit:disabled { opacity: 0.65; cursor: not-allowed; }
      `}</style>
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
              <label className="flex flex-col gap-1.5">
                <span style={labelStyle}>New password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => {
                    if (password && password.length < 8)
                      setFieldError('password', 'Use at least 8 characters.')
                    else clearFieldError('password')
                  }}
                  required
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className="upw-field"
                  aria-invalid={fieldErrors.password ? true : undefined}
                  aria-describedby={fieldErrors.password ? 'upw-pw-err' : undefined}
                />
                {fieldErrors.password && (
                  <span id="upw-pw-err" role="alert" style={{ fontSize: 11.5, color: 'var(--err)' }}>
                    {fieldErrors.password}
                  </span>
                )}
              </label>
              <label className="flex flex-col gap-1.5">
                <span style={labelStyle}>Confirm new password</span>
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  onBlur={() => {
                    if (confirm && confirm !== password)
                      setFieldError('confirm', 'Passwords do not match.')
                    else clearFieldError('confirm')
                  }}
                  required
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className="upw-field"
                  aria-invalid={fieldErrors.confirm ? true : undefined}
                  aria-describedby={fieldErrors.confirm ? 'upw-conf-err' : undefined}
                />
                {fieldErrors.confirm && (
                  <span id="upw-conf-err" role="alert" style={{ fontSize: 11.5, color: 'var(--err)' }}>
                    {fieldErrors.confirm}
                  </span>
                )}
              </label>
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
                className="upw-submit"
                style={{ marginTop: 4 }}
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
const labelStyle: React.CSSProperties = {
  fontSize: 11.5,
  fontWeight: 600,
  color: 'var(--ink-2)',
}
