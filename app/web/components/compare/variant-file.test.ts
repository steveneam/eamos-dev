import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  readCompareVariants,
  stashCompareSources,
  type ImportSource,
} from '@/lib/variant-file'

function storageMock(): Storage {
  const values = new Map<string, string>()
  return {
    get length() {
      return values.size
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => {
      values.delete(key)
    },
    setItem: (key, value) => values.set(key, value),
  }
}

beforeEach(() => {
  vi.stubGlobal('window', { sessionStorage: storageMock() })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Batch source handoff', () => {
  it('preserves a truncated marker and requires full-file reattachment after refresh', () => {
    const source: ImportSource = {
      id: 'source-1',
      name: 'large.vcf',
      kind: 'file',
      variants: [{ raw: '1 100 . A G', gene: null, variant: null, query: '1-100-A-G' }],
      clientTruncated: true,
      clientParseLimit: 2_000,
      clientParsedCount: 2_001,
    }

    stashCompareSources([source])
    const restored = readCompareVariants()

    expect(restored?.sources[0]).toMatchObject({
      clientTruncated: true,
      clientParseLimit: 2_000,
      clientParsedCount: 2_001,
      requiresFileReattach: true,
    })
  })

  it('does not require reattachment for a complete browser cohort', () => {
    stashCompareSources([
      {
        id: 'source-2',
        name: 'small.tsv',
        kind: 'file',
        variants: [{ raw: 'RPE65 c.260A>G', gene: 'RPE65', variant: 'c.260A>G', query: 'RPE65 c.260A>G' }],
      },
    ])

    expect(readCompareVariants()?.sources[0]?.requiresFileReattach).toBe(false)
  })
})
