import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

// Server-side Supabase client (Route Handlers / Server Components). Shares the
// cookie session with the browser client (@supabase/ssr), so a session set here
// (e.g. the /auth/confirm email-link handler) is immediately visible to the
// browser client → the user lands signed in. Reads PUBLIC env only.
export async function createClient() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            )
          } catch {
            // Called from a Server Component (read-only cookies) — safe to ignore.
          }
        },
      },
    },
  )
}
