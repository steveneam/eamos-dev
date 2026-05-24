'use client'
import { useState, type FormEvent } from 'react'
import { useAuth, type OAuthProvider } from '@/components/auth/AuthProvider'

type Mode = 'signup' | 'login' | 'reset' | 'success'

// Apple/ORCID are phase-2 (user 2026-05-24) — AuthProvider still supports 'apple'
// if re-added here later.
const OAUTH: { id: OAuthProvider; label: string; icon: React.ReactNode }[] = [
  { id: 'google', label: 'Google', icon: <GoogleIcon /> },
  { id: 'azure', label: 'Microsoft', icon: <MicrosoftIcon /> },
  { id: 'linkedin_oidc', label: 'LinkedIn', icon: <LinkedInIcon /> },
]

export function AuthPanel({ onClose }: { onClose: () => void }) {
  const { signInWithPassword, signUp, signInWithOAuth, resetPassword, configured } = useAuth()
  const [mode, setMode] = useState<Mode>('signup')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [receipt, setReceipt] = useState<{ confirmed: boolean }>({ confirmed: true })

  const reset = () => {
    setError(null)
    setNotice(null)
  }

  const onOAuth = async (provider: OAuthProvider) => {
    reset()
    setBusy(true)
    const { error } = await signInWithOAuth(provider)
    if (error) {
      setError(error)
      setBusy(false)
    }
    // On success the browser redirects to the provider — no further UI needed.
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    reset()

    if (mode === 'reset') {
      setBusy(true)
      const { error } = await resetPassword(email)
      setBusy(false)
      if (error) return setError(error)
      setNotice('If that email has an account, a reset link is on its way.')
      return
    }

    if (mode === 'signup') {
      if (password !== confirm) return setError('Passwords do not match.')
      if (password.length < 8) return setError('Use at least 8 characters.')
      if (!agreed) return setError('Please accept the Terms & Conditions.')
      setBusy(true)
      const { error, needsConfirmation } = await signUp(email, password)
      setBusy(false)
      if (error) return setError(error)
      setReceipt({ confirmed: !needsConfirmation })
      setMode('success')
      return
    }

    // login
    setBusy(true)
    const { error } = await signInWithPassword(email, password)
    setBusy(false)
    if (error) return setError(error)
    onClose() // signed in — AuthMenu re-renders to the signed-in state
  }

  if (mode === 'success') {
    return (
      <div style={{ padding: '28px 24px', textAlign: 'center' }}>
        <div
          style={{
            width: 52,
            height: 52,
            margin: '4px auto 16px',
            borderRadius: 999,
            background: 'rgba(16,185,129,0.16)',
            display: 'grid',
            placeItems: 'center',
            border: '0.5px solid rgba(52,211,153,0.5)',
          }}
        >
          <CheckIcon />
        </div>
        <h3 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 18, color: 'var(--hero-ink)', margin: 0 }}>
          {receipt.confirmed ? 'Account created — you’re in' : 'Account created'}
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--hero-ink-2)', margin: '8px 0 0' }}>
          {receipt.confirmed
            ? 'Welcome to Eamos. Your researcher workspace is ready.'
            : 'Check your inbox to confirm your email, then sign in.'}
        </p>
        {email && (
          <p style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--hero-ink-3)', margin: '10px 0 0' }}>
            {email}
          </p>
        )}
        <button type="button" onClick={onClose} style={primaryBtn} className="mt-5 w-full">
          {receipt.confirmed ? 'Continue' : 'Done'}
        </button>
      </div>
    )
  }

  const isSignup = mode === 'signup'
  const isReset = mode === 'reset'

  return (
    <div style={{ padding: '20px 22px 22px' }}>
      <header className="mb-4 flex items-center justify-between">
        <h3 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 16.5, color: 'var(--hero-ink)', margin: 0 }}>
          {isReset ? 'Reset password' : isSignup ? 'Create your account' : 'Welcome back'}
        </h3>
        <button type="button" onClick={onClose} aria-label="Close" style={iconBtn}>
          <CloseIcon />
        </button>
      </header>

      {!configured && (
        <p style={noticeBox} role="status">
          Demo mode — connect Supabase env to enable live sign-in.
        </p>
      )}

      {!isReset && (
        <>
          <div className="grid grid-cols-3 gap-2">
            {OAUTH.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => onOAuth(p.id)}
                disabled={busy}
                aria-label={`Continue with ${p.label}`}
                title={`Continue with ${p.label}`}
                style={oauthBtn}
                className="auth-oauth"
              >
                {p.icon}
              </button>
            ))}
          </div>
          <div className="my-4 flex items-center gap-3">
            <span style={{ flex: 1, height: '0.5px', background: 'var(--hero-line)' }} />
            <span style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--hero-ink-3)' }}>
              or with email
            </span>
            <span style={{ flex: 1, height: '0.5px', background: 'var(--hero-line)' }} />
          </div>
        </>
      )}

      <form onSubmit={onSubmit} className="flex flex-col gap-2.5">
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" placeholder="you@lab.org" />

        {!isReset && (
          <Field
            label={isSignup ? 'Create password' : 'Password'}
            type="password"
            value={password}
            onChange={setPassword}
            autoComplete={isSignup ? 'new-password' : 'current-password'}
            placeholder="••••••••"
          />
        )}
        {isSignup && (
          <Field
            label="Confirm password"
            type="password"
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
            placeholder="••••••••"
          />
        )}

        {isSignup && (
          <label className="mt-1 flex items-start gap-2.5" style={{ cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              style={{ marginTop: 2, accentColor: 'var(--em)', width: 15, height: 15 }}
            />
            <span style={{ fontSize: 12, lineHeight: 1.5, color: 'var(--hero-ink-2)' }}>
              I agree to the{' '}
              <a href="/terms" target="_blank" rel="noreferrer" style={{ color: 'var(--em-bright)', textDecoration: 'none' }}>
                Terms &amp; Conditions
              </a>
              .
            </span>
          </label>
        )}

        {!isSignup && !isReset && (
          <button
            type="button"
            onClick={() => {
              reset()
              setMode('reset')
            }}
            style={{ alignSelf: 'flex-end', fontSize: 12, color: 'var(--hero-ink-2)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            Forgot password?
          </button>
        )}

        {error && <p style={errorBox} role="alert">{error}</p>}
        {notice && <p style={noticeBox} role="status">{notice}</p>}

        <div className="mt-2 flex items-center gap-2.5">
          <button type="button" onClick={onClose} style={ghostBtn} disabled={busy}>
            Cancel
          </button>
          <button type="submit" style={{ ...primaryBtn, flex: 1, opacity: busy ? 0.7 : 1 }} disabled={busy}>
            {busy ? 'Working…' : isReset ? 'Send reset link' : isSignup ? 'Sign up' : 'Sign in'}
          </button>
        </div>
      </form>

      <p className="mt-4 text-center" style={{ fontSize: 12.5, color: 'var(--hero-ink-3)' }}>
        {isReset ? (
          <button type="button" onClick={() => { reset(); setMode('login') }} style={linkBtn}>
            ← Back to sign in
          </button>
        ) : isSignup ? (
          <>
            Already have an account?{' '}
            <button type="button" onClick={() => { reset(); setMode('login') }} style={linkBtn}>
              Log in
            </button>
          </>
        ) : (
          <>
            New to Eamos?{' '}
            <button type="button" onClick={() => { reset(); setMode('signup') }} style={linkBtn}>
              Create an account
            </button>
          </>
        )}
      </p>
    </div>
  )
}

function Field({
  label,
  type,
  value,
  onChange,
  autoComplete,
  placeholder,
}: {
  label: string
  type: string
  value: string
  onChange: (v: string) => void
  autoComplete?: string
  placeholder?: string
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--hero-ink-2)' }}>{label}</span>
      <input
        data-tone="dark"
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        autoComplete={autoComplete}
        placeholder={placeholder}
        spellCheck={false}
        style={inputStyle}
      />
    </label>
  )
}

// ── styles ──────────────────────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  width: '100%',
  height: 40,
  padding: '0 12px',
  borderRadius: 10,
  background: 'var(--hero-glass)',
  border: '0.5px solid var(--hero-line)',
  color: 'var(--hero-ink)',
  fontSize: 13.5,
  outline: 'none',
}
const primaryBtn: React.CSSProperties = {
  height: 40,
  borderRadius: 10,
  border: 'none',
  background: 'var(--em)',
  color: '#04140e',
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
}
const ghostBtn: React.CSSProperties = {
  height: 40,
  padding: '0 16px',
  borderRadius: 10,
  background: 'var(--hero-glass)',
  border: '0.5px solid var(--hero-line)',
  color: 'var(--hero-ink-2)',
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
}
const oauthBtn: React.CSSProperties = {
  height: 42,
  display: 'grid',
  placeItems: 'center',
  borderRadius: 10,
  background: 'var(--hero-glass2)',
  border: '0.5px solid var(--hero-line)',
  color: 'var(--hero-ink)',
  cursor: 'pointer',
}
const iconBtn: React.CSSProperties = {
  width: 28,
  height: 28,
  display: 'grid',
  placeItems: 'center',
  borderRadius: 8,
  background: 'transparent',
  border: 'none',
  color: 'var(--hero-ink-3)',
  cursor: 'pointer',
}
const linkBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  padding: 0,
  color: 'var(--em-bright)',
  fontWeight: 600,
  cursor: 'pointer',
  fontSize: 12.5,
}
const errorBox: React.CSSProperties = {
  margin: 0,
  padding: '8px 11px',
  borderRadius: 8,
  background: 'rgba(220,80,70,0.14)',
  border: '0.5px solid rgba(220,80,70,0.4)',
  color: '#fca5a5',
  fontSize: 12,
  lineHeight: 1.45,
}
const noticeBox: React.CSSProperties = {
  margin: 0,
  padding: '8px 11px',
  borderRadius: 8,
  background: 'var(--hero-glass)',
  border: '0.5px solid var(--hero-line)',
  color: 'var(--hero-ink-2)',
  fontSize: 12,
  lineHeight: 1.45,
}

// ── brand icons (compact marks) ──────────────────────────────────────────────
function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1Z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z" />
      <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.3 9.14 5.38 12 5.38Z" />
    </svg>
  )
}
function MicrosoftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 23 23" aria-hidden>
      <path fill="#F25022" d="M1 1h10v10H1z" />
      <path fill="#7FBA00" d="M12 1h10v10H12z" />
      <path fill="#00A4EF" d="M1 12h10v10H1z" />
      <path fill="#FFB900" d="M12 12h10v10H12z" />
    </svg>
  )
}
function LinkedInIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden>
      <path fill="#0A66C2" d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.07 2.07 0 1 1 0-4.13 2.07 2.07 0 0 1 0 4.13ZM7.12 20.45H3.55V9h3.57v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  )
}
function CheckIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--em-bright)" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}
function CloseIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}
