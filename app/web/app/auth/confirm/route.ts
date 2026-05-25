import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

// Supabase email-link OTP types (typed locally to avoid importing from
// @supabase/supabase-js, matching the rest of the auth code).
type EmailOtpType = 'email' | 'signup' | 'recovery' | 'invite' | 'magiclink' | 'email_change'

// Email confirmation / password-recovery callback.
//
// Supabase emails link here with a token_hash; we verify it server-side, which
// sets the session cookie, so the user lands ALREADY SIGNED IN (no re-login).
// Point the Supabase "Confirm signup" email template at:
//   {{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email&next=/account
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const token_hash = searchParams.get('token_hash')
  const type = searchParams.get('type') as EmailOtpType | null
  const nextParam = searchParams.get('next') ?? '/account'
  // Open-redirect guard: only same-origin relative paths.
  const next =
    nextParam.startsWith('/') && !nextParam.startsWith('//') ? nextParam : '/account'

  // Honour Vercel's forwarded host so the redirect lands on the public domain.
  const forwardedHost = request.headers.get('x-forwarded-host')
  const base = forwardedHost ? `https://${forwardedHost}` : origin

  if (token_hash && type) {
    const supabase = await createClient()
    const { error } = await supabase.auth.verifyOtp({ type, token_hash })
    if (!error) return NextResponse.redirect(`${base}${next}`)
  }

  // Missing/invalid/expired token → land on the account page (the auth panel can
  // prompt a manual sign-in).
  return NextResponse.redirect(`${base}/account?confirm=failed`)
}
