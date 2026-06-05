import type { ParsedVariant } from './variant-file'

export interface SavedVariant {
  id: string
  gene: string | null
  variant: string | null
  query: string
  raw: string
  savedAt: number
  folderId: string | null
}

export interface Folder {
  id: string
  name: string
  createdAt: number
}

interface LibraryStore {
  variants: SavedVariant[]
  folders: Folder[]
}

const STORAGE_KEY = 'eamos.library.v1'
const CHANGE_EVENT = 'eamos:library-change'

const EMPTY: LibraryStore = { variants: [], folders: [] }

export function getLibrary(): LibraryStore {
  if (typeof window === 'undefined') return EMPTY
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

function persist(store: LibraryStore): void {
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
  window.addEventListener(CHANGE_EVENT, cb)
  window.addEventListener('storage', cb)
  return () => {
    window.removeEventListener(CHANGE_EVENT, cb)
    window.removeEventListener('storage', cb)
  }
}
