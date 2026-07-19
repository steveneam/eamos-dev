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
  classification?: ClassificationTier | null
  /** Full transcript-qualified HGVS (e.g. NM_206933.4:c.2276G>T) for the card's
   *  progressive-disclosure "view more"; the compact `query` stays the round-trip key. */
  hgvs_full?: string | null
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

const LEGACY_STORAGE_KEY = 'eamos.library.v1'
const STORAGE_PREFIX = 'eamos.library.v2'
const CHANGE_EVENT = 'eamos:library-change'
const VIEW_EVENT = 'eamos:library-view-change'

export const LIBRARY_SCHEMA_ID = '__eamos_schema__:v2'
export const LIBRARY_TOMBSTONE_PREFIX = '__eamos_tombstone__:'

const EMPTY: LibraryStore = { variants: [], folders: [] }

// Memoized snapshot so getLibrary() returns a STABLE reference between changes —
// required by useSyncExternalStore (a fresh object every call loops on identity).
// persist() refreshes the memo for same-tab writes; the cross-tab 'storage'
// listener in subscribe() invalidates it so the next read re-parses.
let cached: LibraryStore | null = null
let visibleCached: { source: LibraryStore; value: LibraryStore } | null = null
let activeScope = 'anonymous'

function rotateRight(value: number, count: number): number {
  return (value >>> count) | (value << (32 - count))
}

/** Small synchronous SHA-256 implementation used only to derive opaque local
 *  storage/tombstone keys. Keeping this synchronous means a delete is visible
 *  to every mounted Library surface in the same interaction frame. */
export function sha256Hex(value: string): string {
  const bytes = new TextEncoder().encode(value)
  const bitLength = bytes.length * 8
  const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64
  const padded = new Uint8Array(paddedLength)
  padded.set(bytes)
  padded[bytes.length] = 0x80
  const view = new DataView(padded.buffer)
  view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000), false)
  view.setUint32(paddedLength - 4, bitLength >>> 0, false)

  const constants = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
    0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
    0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
    0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
    0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
    0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
    0xc67178f2,
  ])
  const hash = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ])
  const words = new Uint32Array(64)

  for (let offset = 0; offset < paddedLength; offset += 64) {
    for (let index = 0; index < 16; index += 1) words[index] = view.getUint32(offset + index * 4, false)
    for (let index = 16; index < 64; index += 1) {
      const before15 = words[index - 15]
      const before2 = words[index - 2]
      const sigma0 = rotateRight(before15, 7) ^ rotateRight(before15, 18) ^ (before15 >>> 3)
      const sigma1 = rotateRight(before2, 17) ^ rotateRight(before2, 19) ^ (before2 >>> 10)
      words[index] = (words[index - 16] + sigma0 + words[index - 7] + sigma1) >>> 0
    }
    let [a, b, c, d, e, f, g, h] = hash
    for (let index = 0; index < 64; index += 1) {
      const sigma1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25)
      const choice = (e & f) ^ (~e & g)
      const temp1 = (h + sigma1 + choice + constants[index] + words[index]) >>> 0
      const sigma0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)
      const majority = (a & b) ^ (a & c) ^ (b & c)
      const temp2 = (sigma0 + majority) >>> 0
      h = g
      g = f
      f = e
      e = (d + temp1) >>> 0
      d = c
      c = b
      b = a
      a = (temp1 + temp2) >>> 0
    }
    hash[0] = (hash[0] + a) >>> 0
    hash[1] = (hash[1] + b) >>> 0
    hash[2] = (hash[2] + c) >>> 0
    hash[3] = (hash[3] + d) >>> 0
    hash[4] = (hash[4] + e) >>> 0
    hash[5] = (hash[5] + f) >>> 0
    hash[6] = (hash[6] + g) >>> 0
    hash[7] = (hash[7] + h) >>> 0
  }

  return [...hash].map((part) => part.toString(16).padStart(8, '0')).join('')
}

function storageKey(): string {
  return activeScope === 'anonymous' ? `${STORAGE_PREFIX}:anonymous` : `${STORAGE_PREFIX}:account:${activeScope}`
}

export function isLibrarySchemaRow(variant: SavedVariant): boolean {
  return variant.id === LIBRARY_SCHEMA_ID
}

export function isLibraryTombstone(variant: SavedVariant): boolean {
  return variant.id.startsWith(LIBRARY_TOMBSTONE_PREFIX)
}

export function isLibraryReservedRow(variant: SavedVariant): boolean {
  return isLibrarySchemaRow(variant) || isLibraryTombstone(variant)
}

export function libraryIdentity(variant: SavedVariant): string | null {
  if (isLibrarySchemaRow(variant)) return null
  return (isLibraryTombstone(variant) ? variant.query : variant.id).trim().toLowerCase()
}

function schemaMarker(timestamp = Date.now()): SavedVariant {
  return {
    id: LIBRARY_SCHEMA_ID,
    gene: null,
    variant: null,
    query: 'library.v2',
    raw: '',
    savedAt: timestamp,
    folderId: null,
    classification: null,
    hgvs_full: null,
  }
}

function tombstone(id: string, timestamp: number): SavedVariant {
  return {
    id: `${LIBRARY_TOMBSTONE_PREFIX}${sha256Hex(id)}`,
    gene: null,
    variant: null,
    query: id,
    raw: '',
    savedAt: timestamp,
    folderId: null,
    classification: null,
    hgvs_full: null,
  }
}

export function ensureLibraryV2(store: LibraryStore, timestamp = Date.now()): LibraryStore {
  if (store.variants.some(isLibrarySchemaRow)) return store
  return { ...store, variants: [...store.variants, schemaMarker(timestamp)] }
}

function readStore(): LibraryStore {
  try {
    const key = storageKey()
    let raw = window.localStorage.getItem(key)
    let migrated = false
    if (!raw && activeScope === 'anonymous') {
      raw = window.localStorage.getItem(LEGACY_STORAGE_KEY)
      migrated = Boolean(raw)
    }
    if (!raw) return EMPTY
    const parsed = JSON.parse(raw) as LibraryStore
    if (!Array.isArray(parsed.variants) || !Array.isArray(parsed.folders)) return EMPTY
    const next = ensureLibraryV2(parsed)
    if (migrated) {
      window.localStorage.setItem(key, JSON.stringify(next))
      window.localStorage.removeItem(LEGACY_STORAGE_KEY)
    }
    return next
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

/** User-facing snapshot. Reserved schema and deletion records never reach
 *  Library cards, search, or Batch handoff code, while getLibrary() retains
 *  them for deterministic local/remote sync. */
export function getVisibleLibrary(): LibraryStore {
  const source = getLibrary()
  if (visibleCached?.source === source) return visibleCached.value
  const value = filterLibraryForDisplay(source)
  visibleCached = { source, value }
  return value
}

export function filterLibraryForDisplay(store: LibraryStore): LibraryStore {
  return {
    variants: store.variants.filter((variant) => !isLibraryReservedRow(variant)),
    folders: store.folders,
  }
}

/** Switches between an anonymous device cache and a one-way-hashed account
 *  cache. A second account can never inherit the previous account's browser
 *  snapshot, and anonymous rows are not silently uploaded on sign-in. */
export function setLibraryScope(userId: string | null): void {
  if (typeof window === 'undefined') return
  const nextScope = userId ? sha256Hex(userId) : 'anonymous'
  if (nextScope === activeScope) return
  activeScope = nextScope
  cached = null
  visibleCached = null
  dispatch(VIEW_EVENT)
}

/** Purges only this browser's active account/anonymous cache. Remote account
 *  data is intentionally not rewritten as a side effect of a local-data clear. */
export function clearLocalLibrary(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(storageKey())
    if (activeScope === 'anonymous') window.localStorage.removeItem(LEGACY_STORAGE_KEY)
  } catch {
    // localStorage unavailable — still clear the in-memory view.
  }
  cached = EMPTY
  visibleCached = null
  dispatch(VIEW_EVENT)
}

function persist(store: LibraryStore): void {
  cached = ensureLibraryV2(store) // keep the memo authoritative for same-tab reads
  visibleCached = null
  try {
    window.localStorage.setItem(storageKey(), JSON.stringify(cached))
  } catch {
    // localStorage unavailable (private mode / quota) — non-fatal.
  }
}

function dispatch(eventName = CHANGE_EVENT): void {
  try {
    window.dispatchEvent(new CustomEvent(eventName))
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
  const existingIds = new Set(
    store.variants.filter((variant) => !isLibraryReservedRow(variant)).map((variant) => variant.id),
  )
  const toAdd: SavedVariant[] = []
  const revivedIds = new Set<string>()
  let timestamp = Date.now()
  for (const v of variants) {
    const id = v.query.toLowerCase()
    if (existingIds.has(id)) continue
    existingIds.add(id)
    const deletedAt = store.variants
      .filter((row) => isLibraryTombstone(row) && libraryIdentity(row) === id)
      .reduce((latest, row) => Math.max(latest, row.savedAt), -1)
    timestamp = Math.max(timestamp, deletedAt + 1)
    revivedIds.add(id)
    toAdd.push({
      id,
      gene: v.gene,
      variant: v.variant,
      query: v.query,
      raw: v.raw,
      savedAt: timestamp,
      folderId: folderId ?? null,
    })
  }
  if (toAdd.length === 0) return 0
  const next: LibraryStore = {
    variants: [
      ...store.variants.filter(
        (row) => !(isLibraryTombstone(row) && revivedIds.has(libraryIdentity(row) ?? '')),
      ),
      ...toAdd,
    ],
    folders: store.folders,
  }
  persist(next)
  dispatch()
  return toAdd.length
}

export function removeVariant(id: string): void {
  if (typeof window === 'undefined') return
  const store = getLibrary()
  const normalized = id.trim().toLowerCase()
  const active = store.variants.find((row) => !isLibraryReservedRow(row) && row.id === normalized)
  if (!active) return
  const deletedAt = Math.max(Date.now(), active.savedAt + 1)
  const next: LibraryStore = {
    variants: [
      ...store.variants.filter((row) => libraryIdentity(row) !== normalized),
      tombstone(normalized, deletedAt),
    ],
    folders: store.folders,
  }
  persist(next)
  dispatch()
}

export function isSaved(query: string): boolean {
  if (typeof window === 'undefined') return false
  const store = getLibrary()
  const id = query.toLowerCase()
  return store.variants.some((v) => !isLibraryReservedRow(v) && v.id === id)
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
  window.addEventListener(VIEW_EVENT, cb)
  window.addEventListener('storage', onStorage)
  return () => {
    window.removeEventListener(CHANGE_EVENT, cb)
    window.removeEventListener(VIEW_EVENT, cb)
    window.removeEventListener('storage', onStorage)
  }
}

/** Sync subscribers intentionally exclude view-only purge/scope events. */
export function subscribeForSync(cb: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  window.addEventListener(CHANGE_EVENT, cb)
  return () => window.removeEventListener(CHANGE_EVENT, cb)
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
  if (store.variants.some((x) => !isLibraryReservedRow(x) && x.id === id)) return false
  const deletedAt = store.variants
    .filter((row) => isLibraryTombstone(row) && libraryIdentity(row) === id)
    .reduce((latest, row) => Math.max(latest, row.savedAt), -1)
  const saved: SavedVariant = {
    id,
    gene: v.gene,
    variant: v.variant,
    query: v.query,
    raw: v.raw,
    savedAt: Math.max(Date.now(), deletedAt + 1),
    folderId: meta?.folderId ?? null,
    classification: meta?.classification,
    hgvs_full: meta?.hgvs_full,
  }
  persist({
    variants: [
      ...store.variants.filter((row) => !(isLibraryTombstone(row) && libraryIdentity(row) === id)),
      saved,
    ],
    folders: store.folders,
  })
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
    variants: store.variants.map((v) =>
      v.folderId === id ? { ...v, folderId: null, savedAt: Math.max(Date.now(), v.savedAt + 1) } : v,
    ),
    folders: store.folders.filter((f) => f.id !== id),
  })
  dispatch()
}

/** Re-file a saved variant into a folder (or back to top-level with null). */
export function moveVariant(id: string, targetFolderId: string | null): void {
  if (typeof window === 'undefined') return
  const store = getLibrary()
  persist({
    variants: store.variants.map((v) =>
      v.id === id ? { ...v, folderId: targetFolderId, savedAt: Math.max(Date.now(), v.savedAt + 1) } : v,
    ),
    folders: store.folders,
  })
  dispatch()
}
