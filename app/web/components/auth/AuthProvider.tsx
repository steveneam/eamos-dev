'use client'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { createClient } from '@/utils/supabase/client'

export type OAuthProvider = 'google' | 'azure' | 'linkedin_oidc' | 'apple'

// Derive the client type locally so we don't import from @supabase/supabase-js
// (a transitive dep). We only consume id/email off the user.
type SupabaseClient = ReturnType<typeof createClient>
export interface AuthUser {
  id: string
  email?: string
}

export interface AuthResult {
  error?: string
  /** signUp with email confirmation still ON returns no session → user must confirm. */
  needsConfirmation?: boolean
}

interface AuthContextValue {
  /** Whether NEXT_PUBLIC_SUPABASE_* env is present. False → auth is mock/disabled. */
  configured: boolean
  loading: boolean
  user: AuthUser | null
  signInWithPassword: (email: string, password: string) => Promise<AuthResult>
  signUp: (email: string, password: string) => Promise<AuthResult>
  signInWithOAuth: (provider: OAuthProvider) => Promise<AuthResult>
  resetPassword: (email: string) => Promise<AuthResult>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const NOT_CONFIGURED: AuthResult = {
  error:
    'Auth is not configured yet — set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.',
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // Create the browser client once, but only when the public env is present.
  // Without it (e.g. a local run with no .env.local) we run in a graceful
  // "not configured" mode instead of throwing on mount.
  const client = useMemo<SupabaseClient | null>(() => {
    if (
      !process.env.NEXT_PUBLIC_SUPABASE_URL ||
      !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    ) {
      return null
    }
    try {
      return createClient()
    } catch {
      return null
    }
  }, [])

  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!client) {
      setLoading(false)
      return
    }
    let active = true
    client.auth.getSession().then(({ data }) => {
      if (!active) return
      setUser(toUser(data.session?.user))
      setLoading(false)
    })
    const { data: sub } = client.auth.onAuthStateChange((_event, session) => {
      setUser(toUser(session?.user))
    })
    return () => {
      active = false
      sub.subscription.unsubscribe()
    }
  }, [client])

  const signInWithPassword = useCallback(
    async (email: string, password: string): Promise<AuthResult> => {
      if (!client) return NOT_CONFIGURED
      const { error } = await client.auth.signInWithPassword({ email, password })
      return error ? { error: error.message } : {}
    },
    [client],
  )

  const signUp = useCallback(
    async (email: string, password: string): Promise<AuthResult> => {
      if (!client) return NOT_CONFIGURED
      const { data, error } = await client.auth.signUp({ email, password })
      if (error) return { error: error.message }
      // With "Confirm email" OFF (the user's auto-confirm decision) signUp returns
      // a live session immediately. With it ON, session is null until they confirm.
      return { needsConfirmation: !data.session }
    },
    [client],
  )

  const signInWithOAuth = useCallback(
    async (provider: OAuthProvider): Promise<AuthResult> => {
      if (!client) return NOT_CONFIGURED
      const { error } = await client.auth.signInWithOAuth({
        provider,
        options: { redirectTo: window.location.origin },
      })
      return error ? { error: error.message } : {}
    },
    [client],
  )

  const resetPassword = useCallback(
    async (email: string): Promise<AuthResult> => {
      if (!client) return NOT_CONFIGURED
      const { error } = await client.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/account`,
      })
      return error ? { error: error.message } : {}
    },
    [client],
  )

  const signOut = useCallback(async () => {
    if (!client) return
    await client.auth.signOut()
  }, [client])

  const value = useMemo<AuthContextValue>(
    () => ({
      configured: !!client,
      loading,
      user,
      signInWithPassword,
      signUp,
      signInWithOAuth,
      resetPassword,
      signOut,
    }),
    [client, loading, user, signInWithPassword, signUp, signInWithOAuth, resetPassword, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function toUser(u: { id: string; email?: string } | null | undefined): AuthUser | null {
  return u ? { id: u.id, email: u.email } : null
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
