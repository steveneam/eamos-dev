import { describe, expect, it } from 'vitest'
import { mergeStores } from '@/lib/library-sync'
import {
  LIBRARY_SCHEMA_ID,
  LIBRARY_TOMBSTONE_PREFIX,
  filterLibraryForDisplay,
  isLibraryTombstone,
  sha256Hex,
  type LibraryStore,
  type SavedVariant,
} from '@/lib/variant-library'

function active(id: string, savedAt: number, raw = id): SavedVariant {
  return {
    id,
    gene: 'GENE',
    variant: 'c.1A>G',
    query: id,
    raw,
    savedAt,
    folderId: null,
  }
}

function deleted(id: string, savedAt: number): SavedVariant {
  return {
    id: `${LIBRARY_TOMBSTONE_PREFIX}${sha256Hex(id)}`,
    gene: null,
    variant: null,
    query: id,
    raw: '',
    savedAt,
    folderId: null,
    classification: null,
    hgvs_full: null,
  }
}

function store(variants: SavedVariant[]): LibraryStore {
  return { variants, folders: [] }
}

describe('Library v2 merge', () => {
  it('uses the expected SHA-256 encoding for reserved tombstone ids', () => {
    expect(sha256Hex('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
  })

  it('keeps a newer tombstone instead of resurrecting an older active row', () => {
    const merged = mergeStores(store([active('gene c.1a>g', 10)]), store([deleted('gene c.1a>g', 11)]))
    const row = merged.variants.find((variant) => variant.id !== LIBRARY_SCHEMA_ID)

    expect(row && isLibraryTombstone(row)).toBe(true)
    expect(row?.savedAt).toBe(11)
  })

  it('lets a deliberate newer save revive a deleted identity', () => {
    const merged = mergeStores(store([deleted('gene c.1a>g', 10)]), store([active('gene c.1a>g', 11)]))
    const row = merged.variants.find((variant) => variant.id !== LIBRARY_SCHEMA_ID)

    expect(row?.id).toBe('gene c.1a>g')
    expect(row && isLibraryTombstone(row)).toBe(false)
  })

  it('lets a tombstone win an exact timestamp tie', () => {
    const merged = mergeStores(store([active('gene c.1a>g', 10)]), store([deleted('gene c.1a>g', 10)]))
    const row = merged.variants.find((variant) => variant.id !== LIBRARY_SCHEMA_ID)

    expect(row && isLibraryTombstone(row)).toBe(true)
  })

  it('resolves equal active timestamps independently of merge direction', () => {
    const left = store([active('gene c.1a>g', 10, 'alpha')])
    const right = store([active('gene c.1a>g', 10, 'omega')])
    const leftFirst = mergeStores(left, right).variants.find((variant) => variant.id !== LIBRARY_SCHEMA_ID)
    const rightFirst = mergeStores(right, left).variants.find((variant) => variant.id !== LIBRARY_SCHEMA_ID)

    expect(leftFirst).toEqual(rightFirst)
  })

  it('retains exactly one schema marker', () => {
    const merged = mergeStores(store([]), store([]))
    expect(merged.variants.filter((variant) => variant.id === LIBRARY_SCHEMA_ID)).toHaveLength(1)
  })

  it('filters schema and deletion rows out of user-facing Library data', () => {
    const merged = mergeStores(store([active('gene c.1a>g', 10), deleted('other c.2a>g', 12)]), store([]))
    expect(filterLibraryForDisplay(merged).variants.map((variant) => variant.id)).toEqual(['gene c.1a>g'])
  })
})
