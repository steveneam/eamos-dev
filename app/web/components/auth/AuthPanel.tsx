'use client'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useAuth, type OAuthProvider } from '@/components/auth/AuthProvider'

type Mode = 'signup' | 'login' | 'reset' | 'success'

// Apple/ORCID are phase-2 — AuthProvider still supports 'apple' if re-added.
const OAUTH: { id: OAuthProvider; label: string; icon: React.ReactNode }[] = [
  { id: 'google', label: 'Google', icon: <GoogleIcon /> },
  { id: 'azure', label: 'Microsoft', icon: <MicrosoftIcon /> },
  { id: 'linkedin_oidc', label: 'LinkedIn', icon: <LinkedInIcon /> },
]

// Map Supabase raw error strings to plain-language copy.
function humaniseError(raw: string): string {
  const r = raw.toLowerCase()
  if (r.includes('invalid login credentials') || r.includes('invalid email or password'))
    return 'Email or password is incorrect. Check your details and try again.'
  if (r.includes('email not confirmed'))
    return 'Confirm your email first — check your inbox for the verification link.'
  if (r.includes('user already registered') || r.includes('already been registered'))
    return 'An account with this email already exists. Sign in instead.'
  if (r.includes('password should be'))
    return 'Password must be at least 8 characters.'
  if (r.includes('rate limit') || r.includes('too many'))
    return 'Too many attempts — wait a minute, then try again.'
  if (r.includes('network') || r.includes('fetch'))
    return 'Network error. Check your connection and try again.'
  if (r.includes('not configured') || r.includes('supabase_url'))
    return 'Auth is not configured in this environment.'
  return raw
}

type ToneProps = { tone?: 'dark' | 'light' }

export function AuthPanel({ onClose, tone = 'light' }: { onClose: () => void } & ToneProps) {
  const { signInWithPassword, signUp, signInWithOAuth, resetPassword, configured } = useAuth()
  const [mode, setMode] = useState<Mode>('signup')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [busyProvider, setBusyProvider] = useState<OAuthProvider | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [receipt, setReceipt] = useState<{ confirmed: boolean }>({ confirmed: true })
  // Inline field validation state (on blur)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const dark = tone === 'dark'

  const clear = () => {
    setError(null)
    setNotice(null)
    setFieldErrors({})
  }

  const setFieldError = (field: string, msg: string) =>
    setFieldErrors((prev) => ({ ...prev, [field]: msg }))

  const clearFieldError = (field: string) =>
    setFieldErrors((prev) => {
      const next = { ...prev }
      delete next[field]
      return next
    })

  const onOAuth = async (provider: OAuthProvider) => {
    if (busy || busyProvider) return
    clear()
    setBusyProvider(provider)
    setBusy(true)
    const { error } = await signInWithOAuth(provider)
    if (error) {
      setError(humaniseError(error))
      setBusy(false)
      setBusyProvider(null)
    }
    // On success the page redirects; no need to reset busy.
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (busy) return
    clear()

    if (mode === 'reset') {
      setBusy(true)
      const { error } = await resetPassword(email)
      setBusy(false)
      if (error) return setError(humaniseError(error))
      setNotice('If that email has an account, a reset link is on its way.')
      return
    }

    if (mode === 'signup') {
      if (password !== confirm) return setError('Passwords do not match.')
      if (password.length < 8) return setError('Use at least 8 characters.')
      if (!agreed) return setError('Accept the Terms and Conditions to continue.')
      setBusy(true)
      const { error, needsConfirmation } = await signUp(email, password)
      setBusy(false)
      if (error) return setError(humaniseError(error))
      setReceipt({ confirmed: !needsConfirmation })
      setMode('success')
      return
    }

    setBusy(true)
    const { error } = await signInWithPassword(email, password)
    setBusy(false)
    if (error) return setError(humaniseError(error))
    onClose()
  }

  if (mode === 'success') {
    return (
      <SuccessState
        confirmed={receipt.confirmed}
        email={email}
        onClose={onClose}
        dark={dark}
      />
    )
  }

  const isSignup = mode === 'signup'
  const isReset = mode === 'reset'

  return (
    <>
      <AuthPanelStyles />
      <div style={{ padding: '20px 22px 22px' }}>
        <header className="mb-4 flex items-center justify-between">
          <h3
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 400,
              fontSize: 17,
              color: dark ? 'var(--hero-ink)' : 'var(--ink)',
              margin: 0,
              letterSpacing: '-0.01em',
            }}
          >
            {isReset ? 'Reset password' : isSignup ? 'Create your account' : 'Welcome back'}
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="ap-icon-btn"
            data-dark={dark ? '' : undefined}
          >
            <CloseIcon dark={dark} />
          </button>
        </header>

        {!configured && (
          <p style={noticeStyle(dark)} role="status">
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
                  aria-busy={busyProvider === p.id}
                  className="ap-oauth-btn"
                  data-dark={dark ? '' : undefined}
                  data-busy={busyProvider === p.id ? '' : undefined}
                >
                  {busyProvider === p.id ? <MiniSpinner /> : p.icon}
                </button>
              ))}
            </div>
            <div className="my-4 flex items-center gap-3">
              <span
                style={{
                  flex: 1,
                  height: '0.5px',
                  background: dark ? 'var(--hero-line)' : 'var(--line)',
                }}
              />
              <span
                style={{
                  fontSize: 10.5,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: dark ? 'var(--hero-ink-3)' : 'var(--ink-4)',
                }}
              >
                or with email
              </span>
              <span
                style={{
                  flex: 1,
                  height: '0.5px',
                  background: dark ? 'var(--hero-line)' : 'var(--line)',
                }}
              />
            </div>
          </>
        )}

        <form onSubmit={onSubmit} className="flex flex-col gap-2.5" noValidate>
          <Field
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            autoComplete="email"
            placeholder="you@lab.org"
            dark={dark}
            fieldError={fieldErrors.email}
            onBlur={() => {
              if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
                setFieldError('email', 'Enter a valid email address.')
              else clearFieldError('email')
            }}
          />

          {!isReset && (
            <Field
              label={isSignup ? 'Create password' : 'Password'}
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              placeholder="••••••••"
              dark={dark}
              fieldError={fieldErrors.password}
              onBlur={() => {
                if (isSignup && password && password.length < 8)
                  setFieldError('password', 'Use at least 8 characters.')
                else clearFieldError('password')
              }}
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
              dark={dark}
              fieldError={fieldErrors.confirm}
              onBlur={() => {
                if (confirm && confirm !== password)
                  setFieldError('confirm', 'Passwords do not match.')
                else clearFieldError('confirm')
              }}
            />
          )}

          {isSignup && (
            <label className="mt-1 flex items-start gap-2.5" style={{ cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                style={{
                  marginTop: 2,
                  accentColor: 'var(--teal)',
                  width: 15,
                  height: 15,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontSize: 12,
                  lineHeight: 1.5,
                  color: dark ? 'var(--hero-ink-2)' : 'var(--ink-3)',
                }}
              >
                I agree to the{' '}
                <a
                  href="/terms"
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    color: 'var(--teal)',
                    textDecoration: 'none',
                    fontWeight: 600,
                  }}
                >
                  Terms and Conditions
                </a>
                .
              </span>
            </label>
          )}

          {!isSignup && !isReset && (
            <button
              type="button"
              onClick={() => {
                clear()
                setMode('reset')
              }}
              className="ap-link-btn"
              style={{
                alignSelf: 'flex-end',
                fontSize: 12,
                color: dark ? 'var(--hero-ink-2)' : 'var(--ink-3)',
              }}
            >
              Forgot password?
            </button>
          )}

          {error && (
            <p style={errorStyle(dark)} role="alert">
              {error}
            </p>
          )}
          {notice && (
            <p style={noticeStyle(dark)} role="status">
              {notice}
            </p>
          )}

          <div className="mt-2 flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="ap-ghost-btn"
              data-dark={dark ? '' : undefined}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ap-primary-btn"
              style={{ flex: 1, opacity: busy ? 0.65 : 1 }}
              disabled={busy}
              aria-busy={busy}
            >
              {busy ? 'Working…' : isReset ? 'Send reset link' : isSignup ? 'Sign up' : 'Sign in'}
            </button>
          </div>
        </form>

        <p className="mt-4 text-center" style={{ fontSize: 12.5, color: dark ? 'var(--hero-ink-3)' : 'var(--ink-4)' }}>
          {isReset ? (
            <button
              type="button"
              onClick={() => {
                clear()
                setMode('login')
              }}
              className="ap-link-btn"
              style={{ color: 'var(--teal)', fontWeight: 600, fontSize: 12.5 }}
            >
              Back to sign in
            </button>
          ) : isSignup ? (
            <>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => {
                  clear()
                  setMode('login')
                }}
                className="ap-link-btn"
                style={{ color: 'var(--teal)', fontWeight: 600, fontSize: 12.5 }}
              >
                Sign in
              </button>
            </>
          ) : (
            <>
              New to Eamos?{' '}
              <button
                type="button"
                onClick={() => {
                  clear()
                  setMode('signup')
                }}
                className="ap-link-btn"
                style={{ color: 'var(--teal)', fontWeight: 600, fontSize: 12.5 }}
              >
                Create an account
              </button>
            </>
          )}
        </p>
      </div>
    </>
  )
}

function SuccessState({
  confirmed,
  email,
  onClose,
  dark,
}: {
  confirmed: boolean
  email: string
  onClose: () => void
  dark: boolean
}) {
  const btnRef = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    btnRef.current?.focus()
  }, [])

  return (
    <>
      <AuthPanelStyles />
      <div style={{ padding: '28px 24px', textAlign: 'center' }}>
        <div
          style={{
            width: 48,
            height: 48,
            margin: '4px auto 16px',
            borderRadius: 999,
            background: 'var(--teal-tint)',
            display: 'grid',
            placeItems: 'center',
            border: '0.5px solid var(--teal)',
          }}
        >
          <CheckIcon />
        </div>
        <h3
          style={{
            fontFamily: 'var(--display)',
            fontWeight: 400,
            fontSize: 18,
            color: dark ? 'var(--hero-ink)' : 'var(--ink)',
            margin: 0,
            letterSpacing: '-0.01em',
          }}
        >
          {confirmed ? 'Account created' : 'Check your inbox'}
        </h3>
        <p
          style={{
            fontSize: 13.5,
            lineHeight: 1.55,
            color: dark ? 'var(--hero-ink-2)' : 'var(--ink-3)',
            margin: '8px 0 0',
          }}
        >
          {confirmed
            ? 'Your workspace is ready.'
            : 'Confirm your email to activate your account, then sign in.'}
        </p>
        {email && (
          <p
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 12,
              color: dark ? 'var(--hero-ink-3)' : 'var(--ink-4)',
              margin: '10px 0 0',
            }}
          >
            {email}
          </p>
        )}
        <button
          ref={btnRef}
          type="button"
          onClick={onClose}
          className="ap-primary-btn"
          style={{ marginTop: 20, width: '100%' }}
        >
          {confirmed ? 'Continue' : 'Done'}
        </button>
      </div>
    </>
  )
}

function Field({
  label,
  type,
  value,
  onChange,
  autoComplete,
  placeholder,
  dark,
  fieldError,
  onBlur,
}: {
  label: string
  type: string
  value: string
  onChange: (v: string) => void
  autoComplete?: string
  placeholder?: string
  dark: boolean
  fieldError?: string
  onBlur?: () => void
}) {
  const id = `auth-field-${label.toLowerCase().replace(/\s+/g, '-')}`
  const errId = fieldError ? `${id}-err` : undefined

  return (
    <label className="flex flex-col gap-1.5">
      <span
        style={{
          fontSize: 11.5,
          fontWeight: 600,
          color: dark ? 'var(--hero-ink-2)' : 'var(--ink-2)',
        }}
      >
        {label}
      </span>
      <input
        id={id}
        data-tone={dark ? 'dark' : undefined}
        className="ap-field"
        data-error={fieldError ? '' : undefined}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        required
        autoComplete={autoComplete}
        placeholder={placeholder}
        spellCheck={false}
        aria-describedby={errId}
        aria-invalid={fieldError ? true : undefined}
        style={{
          background: dark ? 'var(--hero-glass)' : 'var(--bg)',
          color: dark ? 'var(--hero-ink)' : 'var(--ink)',
        }}
      />
      {fieldError && (
        <span id={errId} role="alert" style={{ fontSize: 11.5, color: 'var(--err)', marginTop: -2 }}>
          {fieldError}
        </span>
      )}
    </label>
  )
}

// ── scoped styles ────────────────────────────────────────────────────────────
function AuthPanelStyles() {
  return (
    <style>{`
      .ap-field {
        width: 100%;
        height: 40px;
        padding: 0 12px;
        border-radius: var(--r-md);
        font-size: 13.5px;
        border: 0.5px solid var(--line-2);
        outline: none;
        transition: border-color var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard);
      }
      .ap-field[data-error] {
        border-color: var(--err);
      }
      .ap-field:focus-visible,
      .ap-field:focus {
        border-color: var(--teal);
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
        outline: none;
      }
      .ap-field[data-error]:focus-visible,
      .ap-field[data-error]:focus {
        border-color: var(--err);
        box-shadow: 0 0 0 3px rgba(184,43,43,0.10);
      }

      .ap-primary-btn {
        height: 40px;
        padding: 0 16px;
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
      .ap-primary-btn:hover:not(:disabled) {
        background: var(--teal-deep);
      }
      .ap-primary-btn:active:not(:disabled) {
        transform: translateY(1px);
      }
      .ap-primary-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.25);
      }
      .ap-primary-btn:disabled {
        cursor: not-allowed;
      }

      .ap-ghost-btn {
        height: 40px;
        padding: 0 16px;
        border-radius: var(--r-md);
        background: transparent;
        border: 0.5px solid var(--line-2);
        color: var(--ink-3);
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: border-color var(--dur-1) var(--ease-standard),
                    color var(--dur-1) var(--ease-standard);
      }
      .ap-ghost-btn[data-dark] {
        border-color: var(--hero-line);
        color: var(--hero-ink-2);
      }
      .ap-ghost-btn:hover:not(:disabled) {
        border-color: var(--ink-4);
        color: var(--ink-2);
      }
      .ap-ghost-btn:active:not(:disabled) {
        transform: translateY(1px);
      }
      .ap-ghost-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
        border-color: var(--teal);
      }
      .ap-ghost-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .ap-oauth-btn {
        height: 42px;
        display: grid;
        place-items: center;
        border-radius: var(--r-md);
        background: var(--bg-soft);
        border: 0.5px solid var(--line);
        color: var(--ink);
        cursor: pointer;
        transition: border-color var(--dur-1) var(--ease-standard),
                    box-shadow var(--dur-1) var(--ease-standard);
      }
      .ap-oauth-btn[data-dark] {
        background: var(--hero-glass2, rgba(255,255,255,0.06));
        border-color: var(--hero-line);
        color: var(--hero-ink);
      }
      .ap-oauth-btn:hover:not(:disabled) {
        border-color: var(--ink-4);
        box-shadow: var(--elev-1);
      }
      .ap-oauth-btn:active:not(:disabled) {
        transform: scale(0.98);
      }
      .ap-oauth-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
        border-color: var(--teal);
      }
      .ap-oauth-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .ap-oauth-btn[data-busy] {
        opacity: 0.7;
      }

      .ap-icon-btn {
        width: 28px;
        height: 28px;
        display: grid;
        place-items: center;
        border-radius: 8px;
        background: transparent;
        border: none;
        cursor: pointer;
        color: var(--ink-4);
        transition: background var(--dur-1) var(--ease-standard);
      }
      .ap-icon-btn:hover {
        background: var(--bg-soft2);
      }
      .ap-icon-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
      }

      .ap-link-btn {
        background: none;
        border: none;
        padding: 0;
        cursor: pointer;
        transition: opacity var(--dur-1) var(--ease-standard);
      }
      .ap-link-btn:hover {
        opacity: 0.75;
      }
      .ap-link-btn:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(29,158,117,0.12);
        border-radius: 3px;
      }
    `}</style>
  )
}

// ── micro spinner ────────────────────────────────────────────────────────────
function MiniSpinner() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      aria-hidden
      style={{ animation: 'ap-spin 0.7s linear infinite' }}
    >
      <style>{`@keyframes ap-spin { to { transform: rotate(360deg); } }`}</style>
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  )
}

// ── styles ──────────────────────────────────────────────────────────────────
function errorStyle(dark: boolean): React.CSSProperties {
  return {
    margin: 0,
    padding: '9px 11px',
    borderRadius: 8,
    background: 'var(--err-tint)',
    border: '0.5px solid rgba(184,43,43,0.3)',
    color: 'var(--err)',
    fontSize: 12,
    lineHeight: 1.5,
  }
}

function noticeStyle(dark: boolean): React.CSSProperties {
  return {
    margin: 0,
    padding: '9px 11px',
    borderRadius: 8,
    background: dark ? 'var(--hero-glass)' : 'var(--bg-soft)',
    border: dark ? '0.5px solid var(--hero-line)' : '0.5px solid var(--line)',
    color: dark ? 'var(--hero-ink-2)' : 'var(--ink-3)',
    fontSize: 12,
    lineHeight: 1.5,
  }
}

// ── brand icons ──────────────────────────────────────────────────────────────
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
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--teal)" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}
function CloseIcon({ dark }: { dark: boolean }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={dark ? 'var(--hero-ink-3)' : 'var(--ink-4)'} strokeWidth={2} strokeLinecap="round" aria-hidden>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}
