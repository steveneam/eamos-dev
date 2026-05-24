import { createBrowserClient } from '@supabase/ssr'

// Browser-side Supabase client. Reads PUBLIC env (publishable/anon key only —
// never the secret key). The DB is protected by Row Level Security, so the anon
// key can only touch rows the signed-in user owns. See
// docs/deployment/README.md §6 and supabase/migrations/0001_submission_ledger.sql.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  )
}
