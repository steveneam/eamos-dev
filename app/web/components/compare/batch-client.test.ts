import { beforeEach, describe, expect, it, vi } from 'vitest'

const getSession = vi.fn()

vi.mock('@/utils/supabase/client', () => ({
  createClient: () => ({ auth: { getSession } }),
}))

import { createBatch, deleteBatchRun, exportBatchRun, listBatchRuns } from '@/lib/batch'

describe('Batch lifecycle client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    getSession.mockResolvedValue({ data: { session: { access_token: 'token-now' } }, error: null })
  })

  it('does not expose a raw backend error body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'private row from uploaded cohort' }),
      { status: 422, headers: { 'Content-Type': 'application/json' } },
    )))

    await expect(createBatch({ variants: [] })).rejects.toThrow('Batch input could not be accepted.')
    await expect(createBatch({ variants: [] })).rejects.not.toThrow('private row')
  })

  it('uses the frozen owner-scoped run list path and parses cursor headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('[]', {
      status: 200,
      headers: { 'X-Next-Cursor': 'next-opaque', 'X-Total-Count': '7' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    const page = await listBatchRuns({ limit: 5, cursor: 'cursor-opaque' })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/batch/runs?limit=5&cursor=cursor-opaque',
      expect.objectContaining({ headers: { Authorization: 'Bearer token-now' } }),
    )
    expect(page).toEqual({ runs: [], nextCursor: 'next-opaque', total: 7 })
  })

  it('validates run ids before lifecycle requests', async () => {
    vi.stubGlobal('fetch', vi.fn())
    await expect(deleteBatchRun('../another-user')).rejects.toThrow('invalid')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('sanitizes export attachment filenames', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('content', {
      status: 200,
      headers: {
        'Content-Disposition': 'attachment; filename="cohort private.tsv"',
        'Content-Type': 'text/tab-separated-values',
      },
    })))

    const exported = await exportBatchRun('run-1', 'tsv')
    expect(exported.filename).toBe('cohort_private.tsv')
  })
})
