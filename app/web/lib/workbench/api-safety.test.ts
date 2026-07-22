import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  alignSequences,
  analyzeTide,
  designGuides,
  designPrimers,
  designScreeningPrimers,
  designSsodn,
  enumerateOffTargets,
  getGeneViewer,
  resolveAlignReference,
  variantLookup,
  WorkbenchApiError,
} from '../api'

describe('Workbench API request safety', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not turn a cancelled engine request into a fixture response', async () => {
    const controller = new AbortController()
    controller.abort(new DOMException('cancelled', 'AbortError'))
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network stopped')))

    await expect(designPrimers(
      { gene: 'RPE65', cdna: 'c.260A>G' },
      { signal: controller.signal },
    )).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('never substitutes the cropped default fixture for a full-gene request', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(getGeneViewer({
      gene: 'RPE65',
      cdna: 'c.260A>G',
      window: { kind: 'full_gene' },
    })).rejects.toBeInstanceOf(WorkbenchApiError)
  })

  it('rejects fixture-disclosed tool output instead of rendering it as a result', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      mode: 'sanger',
      pairs: [],
      source_disclosure: {
        source_status: 'fixture',
        provider_id: 'workbench_primer_fixture',
        provider_label: 'Fixture primer provider',
        warnings: [],
        requirements: [],
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    await expect(designPrimers({ gene: 'RPE65', cdna: 'c.260A>G' }))
      .rejects.toBeInstanceOf(WorkbenchApiError)
  })

  it('never silently degrades any Workbench execution endpoint on network failure', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('offline'))
    vi.stubGlobal('fetch', fetchMock)
    const trace = new Blob(['ABIF'], { type: 'application/octet-stream' }) as File
    const requests = [
      () => alignSequences({ gene: 'RPE65', cdna: 'c.260A>G', user_sequence: 'ACGT' }),
      () => resolveAlignReference({ gene: 'RPE65', cdna: 'c.260A>G' }),
      () => designGuides({ gene: 'RPE65', cdna: 'c.260A>G' }),
      () => designSsodn({ gene: 'RPE65', cdna: 'c.260A>G' }),
      () => enumerateOffTargets({ guide: 'A'.repeat(20), on_target_locus: null }),
      () => designScreeningPrimers({ sites: [] }),
      () => analyzeTide(trace, trace, 10),
    ]
    for (const request of requests) {
      await expect(request()).rejects.toBeInstanceOf(WorkbenchApiError)
    }
    expect(fetchMock).toHaveBeenCalledTimes(requests.length)
  })

  it('rejects deterministic illustrative CRISPR scoring even when marked local', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      cas: 'SpCas9',
      guides: [],
      ssodn: null,
      source_disclosure: {
        source_status: 'local_provider',
        provider_id: 'local_deterministic_spcas9',
        provider_label: 'Local deterministic SpCas9',
        warnings: ['advanced_crispr_scoring_gated'],
        requirements: ['spcas9_ngg'],
      },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })))

    await expect(designGuides({ gene: 'RPE65', cdna: 'c.260A>G' }))
      .rejects.toBeInstanceOf(WorkbenchApiError)
  })

  it('normalizes backend bodies to a bounded status-derived error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'provider secret and echoed sequence' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } },
    )))

    const error = await designPrimers({ gene: 'RPE65', cdna: 'c.260A>G' }).catch(
      (caught: unknown) => caught,
    )
    expect(error).toBeInstanceOf(WorkbenchApiError)
    expect((error as Error).message).not.toMatch(/provider secret|echoed sequence/i)
  })

  it('does not retry a cancelled lookup after a network failure', async () => {
    const controller = new AbortController()
    controller.abort(new DOMException('cancelled', 'AbortError'))
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('network stopped'))
    vi.stubGlobal('fetch', fetchMock)

    await expect(variantLookup(
      { gene: 'RPE65', cdna: 'c.260A>G', species: 'human' },
      { signal: controller.signal },
    )).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
