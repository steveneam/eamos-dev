import type { ParsedVariant } from './variant-file'
import type { ClassificationTier } from './backend'

export interface SavedVariant {
  id: string
  gene: string | null
  variant: string | null
  query: string
  raw: string
  savedAt: number
  folderId: string | null
  /** ACMG tier captured at save-time from a report payload, so the saved card
   *  can show a coloured class dot. Absent for cohort rows saved from /compare
   *  (no classification known) → neutral --cls-na dot. */
  classification?: ClassificationTier
  /** Full transcript-qualified HGVS (e.g. NM_206933.4:c.2276G>T) for the card's
   *  progressive-disclosure "view more"; the compact `query` stays the round-trip key. */
  hgvs_full?: string
}

export interface Folder {
  id: string
  name: string
  createdAt: number
}

export interface LibraryStore {
  variants: SavedVariant[]
  folders: Folder[]
}

const STORAGE_KEY = 'eamos.library.v1'
const CHANGE_EVENT = 'eamos:library-change'

const EMPTY: LibraryStore = { variants: [], folders: [] }

// Memoized snapshot so getLibrary() returns a STABLE reference between changes —
// required by useSyncExternalStore (a fresh object every call loops on identity).
// persist() refreshes the memo for same-tab writes; the cross-tab 'storage'
// listener in subscribe() invalidates it so the next read re-parses.
let cached: LibraryStore | null = null

function readStore(): LibraryStore {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return EMPTY
    const parsed = JSON.parse(raw) as LibraryStore
    if (!Array.isArray(parsed.variants) || !Array.isArray(parsed.folders)) return EMPTY
    return parsed
  } catch {
    return EMPTY
  }
}

export function getLibrary(): LibraryStore {
  if (typeof window === 'undefined') return EMPTY
  if (cached) return cached
  cached = readStore()
  return cached
}

function persist(store: LibraryStore): void {
  cached = store // keep the memo authoritative for same-tab reads
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch {
    // localStorage unavailable (private mode / quota) — non-fatal.
  }
}

function dispatch(): void {
  try {
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT))
  } catch {
    // CustomEvent unavailable — non-fatal.
  }
}

/** Replace the entire store — used by account sync to apply a merged library.
 *  Persists + notifies subscribers like the granular mutators. */
export function replaceLibrary(store: LibraryStore): void {
  if (typeof window === 'undefined') return
  persist({ variants: store.variants, folders: store.folders })
  dispatch()
}

export function saveVariants(variants: ParsedVariant[], folderId?: string | null): number {
  if (typeof window === 'undefined') return 0
  const store = getLibrary()
  const existingIds = new Set(store.variants.map((v) => v.id))
  const toAdd: SavedVariant[] = []
  for (const v of variants) {
    const id = v.query.toLowerCase()
    if (existingIds.has(id)) continue
    existingIds.add(id)
    toAdd.push({
      id,
      gene: v.gene,
      variant: v.variant,
      query: v.query,
      raw: v.raw,
      savedAt: Date.now(),
      folderId: folderId ?? null,
    })
  }
  if (toAdd.length === 0) return 0
  const next: LibraryStore = { variants: [...store.variants, ...toAdd], folders: store.folders }
  persist(next)
  dispatch()
  return toAdd.length
}

export function removeVariant(id: string): void {
  if (typeof window === 'undefined') return
  const store = getLibrary()
  const next: LibraryStore = { variants: store.variants.filter((v) => v.id !== id), folders: store.folders }
  persist(next)
  dispatch()
}

export function isSaved(query: string): boolean {
  if (typeof window === 'undefined') return false
  const store = getLibrary()
  const id = query.toLowerCase()
  return store.variants.some((v) => v.id === id)
}

export function subscribe(cb: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  // Cross-tab writes change localStorage under us → drop the memo so the next
  // getLibrary() re-reads. Same-tab writes already refreshed the memo in
  // persist(), so the CHANGE_EVENT handler only needs to notify.
  const onStorage = () => {
    cached = null
    cb()
  }
  window.addEventListener(CHANGE_EVENT, cb)
  window.addEventListener('storage', onStorage)
  return () => {
    window.removeEventListener(CHANGE_EVENT, cb)
    window.removeEventListener('storage', onStorage)
  }
}

/** Single-variant save (the report header "Save current variant" CTA). Mirrors
 *  saveVariants() dedupe (id = query.toLowerCase()); captures the optional
 *  report-time metadata (class tier + full HGVS). Returns true if added. */
export function saveVariant(
  v: ParsedVariant,
  meta?: { folderId?: string | null; classification?: ClassificationTier; hgvs_full?: string },
): boolean {
  if (typeof window === 'undefined') return false
  const store = getLibrary()
  const id = v.query.toLowerCase()
  if (store.variants.some((x) => x.id === id)) return false
  const saved: SavedVariant = {
    id,
    gene: v.gene,
    variant: v.variant,
    query: v.query,
    raw: v.raw,
    savedAt: Date.now(),
    folderId: meta?.folderId ?? null,
    classification: meta?.classification,
    hgvs_full: meta?.hgvs_full,
  }
  persist({ variants: [...store.variants, saved], folders: store.folders })
  dispatch()
  return true
}

// --- Folder CRUD (additive; folders never delete their variants) ---

function folderId(): string {
  return `folder-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

/** Create a folder (trimmed, case-insensitive dedupe). Returns the new — or the
 *  existing same-named — folder, or null on empty name / SSR. */
export function createFolder(name: string): Folder | null {
  if (typeof window === 'undefined') return null
  const trimmed = name.trim()
  if (!trimmed) return null
  const store = getLibrary()
  const existing = store.folders.find((f) => f.name.toLowerCase() === trimmed.toLowerCase())
  if (existing) return existing
  const folder: Folder = { id: folderId(), name: trimmed, createdAt: Date.now() }
  persist({ variants: store.variants, folders: [...store.folders, folder] })
  dispatch()
  return folder
}

export function renameFolder(id: string, name: string): void {
  if (typeof window === 'undefined') return
  const trimmed = name.trim()
  if (!trimmed) return
  const store = getLibrary()
  persist({
    variants: store.variants,
    folders: store.folders.map((f) => (f.id === id ? { ...f, name: trimmed } : f)),
  })
  dispatch()
}

/** Delete a folder; re-files its variants to the top-level list (never deletes them). */
export function removeFolder(id: string): void {
  if (typeof window === 'undefined') return
  const store = getLibrary()
  persist({
    variants: store.variants.map((v) => (v.folderId === id ? { ...v, folderId: null } : v)),
    folders: store.folders.filter((f) => f.id !== id),
  })
  dispatch()
}

/** Re-file a saved variant into a folder (or back to top-level with null). */
export function moveVariant(id: string, targetFolderId: string | null): void {
  if (typeof window === 'undefined') return
  const store = getLibrary()
  persist({
    variants: store.variants.map((v) => (v.id === id ? { ...v, folderId: targetFolderId } : v)),
    folders: store.folders,
  })
  dispatch()
}
