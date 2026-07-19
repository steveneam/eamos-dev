import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CanonicalVariantRefV1 } from './backend'
import {
  ReportWorkflowError,
  clearPaperTarget,
  getCuratedVariants,
  getRelatedVariants,
  readPaperTarget,
  stashPaperTarget,
} from './report-workflow'

const canonical: CanonicalVariantRefV1 = {
  schema_version: 'canonical_variant_ref.v1',
  gene: 'GENE1',
  cdna: 'c.1A>G',
  transcript: 'NM_000001.1',
  protein_hgvs: 'p.Lys1Arg',
  genomic_hg38: '1-100-A-G',
  variant_key: '1-100-A-G',
  species: 'human',
  genome_build: 'GRCh38',
  resolution_status: 'resolved',
  source_support: ['test'],
  warnings: [],
}

function memoryStorage() {
  const values = new Map<string, string>()
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  }
}

describe('Report workflow client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubGlobal('window', { sessionStorage: memoryStorage() })
  })

  it('uses the frozen related-variant query grammar', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], warnings: [] }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await getRelatedVariants({ gene: 'GENE 1', cdna: 'c.1A>G', transcript: 'NM_1.1' })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/lookup/related?gene=GENE+1&cdna=c.1A%3EG&transcript=NM_1.1',
      expect.objectContaining({ signal: undefined }),
    )
  })

  it('uses typed curated filters and an opaque cursor', async () => {
    const response = {
      gene: 'GENE1',
      classification_filter: 'vus',
      consequence_filter: 'missense',
      items: [],
      next_cursor: null,
      total: 0,
      source_disclosure: { source_status: 'available', provider_id: 'local', provider_label: 'Local', warnings: [], requirements: [] },
      warnings: [],
    }
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await getCuratedVariants({ gene: 'GENE1', classification: 'vus', consequence: 'missense', cursor: 'next.1', limit: 20 })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/lookup/curated?gene=GENE1&classification=vus&consequence=missense&limit=20&cursor=next.1')
  })

  it('maps backend bodies to a safe unavailable error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'private server and record detail' }),
      { status: 500 },
    )))

    const error = await getRelatedVariants({ gene: 'GENE1', cdna: 'c.1A>G' }).catch((caught) => caught)
    expect(error).toBeInstanceOf(ReportWorkflowError)
    expect((error as Error).message).not.toContain('private')
  })

  it('carries only bounded variant identity into Paper session context', () => {
    stashPaperTarget(canonical)
    expect(readPaperTarget()?.variant).toEqual(canonical)

    clearPaperTarget()
    expect(readPaperTarget()).toBeNull()
  })
})
