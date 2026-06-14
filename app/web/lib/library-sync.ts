import { createClient } from '@/utils/supabase/client'
import { getLibrary, replaceLibrary, type LibraryStore } from './variant-library'

// Account-synced variant library (docs/library-sync/spec.md). localStorage stays
// the offline cache + anonymous fallback; when signed in we pull the account row,
// union-merge it with local (keep-wins), and the change-subscriber debounce-pushes
// changes back. Endpoints: GET/PUT /api/v1/library (login-gated, Bearer token —
// same Supabase session token the chat client uses).
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

async function accessToken(): Promise<string | null> {
  try {
    const { data } = await createClient().auth.getSession()
    return data.session?.access_token ?? null
  } catch {
    return null
  }
}

function mergeById<T extends { id: string }>(
  local: T[],
  remote: T[],
  keepNewer: (a: T, b: T) => T,
): T[] {
  const byId = new Map<string, T>()
  for (const item of local) byId.set(item.id, item)
  for (const item of remote) {
    const existing = byId.get(item.id)
    byId.set(item.id, existing ? keepNewer(existing, item) : item)
  }
  return [...byId.values()]
}

/** Union-merge two stores by id, keeping the newer item on collision. Favours
 *  not losing a save over propagating deletes (no tombstones in v1 — see spec §5). */
export function mergeStores(local: LibraryStore, remote: LibraryStore): LibraryStore {
  return {
    variants: mergeById(local.variants, remote.variants, (a, b) => (b.savedAt > a.savedAt ? b : a)),
    folders: mergeById(local.folders, remote.folders, (a, b) => (b.createdAt > a.createdAt ? b : a)),
  }
}

export async function fetchRemoteLibrary(signal?: AbortSignal): Promise<LibraryStore | null> {
  const token = await accessToken()
  if (!token) return null
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/library`, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    })
    if (!res.ok) return null
    const data = (await res.json()) as Partial<LibraryStore>
    return { variants: data.variants ?? [], folders: data.folders ?? [] }
  } catch {
    // unreachable / aborted — stay on local.
    return null
  }
}

export async function pushRemoteLibrary(store: LibraryStore): Promise<void> {
  const token = await accessToken()
  if (!token) return
  try {
    await fetch(`${API_BASE_URL}/api/v1/library`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ variants: store.variants, folders: store.folders }),
    })
  } catch {
    // offline — keep local; the next change re-pushes.
  }
}

/** Pull the account library, union-merge with local, persist the result. The
 *  merged superset is pushed back by the change-subscriber in <LibrarySync>. */
export async function pullAndMerge(signal?: AbortSignal): Promise<void> {
  const remote = await fetchRemoteLibrary(signal)
  if (!remote) return // anonymous / offline → local only
  replaceLibrary(mergeStores(getLibrary(), remote))
}
