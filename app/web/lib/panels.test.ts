import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPanel, getPanels, PanelRequestError, resolvePanel } from './panels'
import { MOCK_PANELS } from './panels.mock'

/**
 * A gene panel decides which variants a Batch run reports on, so a panel
 * request that did not succeed must surface as a typed unavailable state. These
 * tests exist because every one of these paths previously returned bundled
 * fixture panels on failure, which reads on the surface as a real panel.
 */
describe('panel API failure states', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not return fixture panels when the catalogue is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network stopped')))

    await expect(getPanels()).rejects.toBeInstanceOf(PanelRequestError)
    await expect(getPanels()).rejects.toMatchObject({ code: 'unavailable' })
  })

  it('does not return a fixture panel when the catalogue errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('upstream exploded', { status: 500 })),
    )

    await expect(getPanels()).rejects.toMatchObject({ code: 'request_failed', status: 500 })
  })

  it('reports a missing panel as not_found rather than substituting a fixture', async () => {
    const knownFixtureSlug = MOCK_PANELS[0].slug
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))

    await expect(getPanel(knownFixtureSlug)).rejects.toMatchObject({ code: 'not_found' })
  })

  it('does not build a stand-in custom panel when resolve fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network stopped')))

    await expect(resolvePanel({ symbols: ['RPE65', 'ABCA4'] })).rejects.toMatchObject({
      code: 'unavailable',
    })
  })

  it('keeps a cancelled panel request as an abort, not an unavailable panel', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new DOMException('cancelled', 'AbortError')),
    )

    await expect(getPanels()).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('does not copy the response body into the surfaced error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('BRCA1,BRCA2,TP53', { status: 500 })),
    )

    await expect(getPanels()).rejects.toSatisfy(
      (err: PanelRequestError) => !err.message.includes('BRCA1'),
    )
  })

  it('returns the live catalogue unchanged on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        Response.json({ panels: [{ slug: 'live-panel', name: 'Live panel', gene_count: 2 }] }),
      ),
    )

    const panels = await getPanels()
    expect(panels).toHaveLength(1)
    expect(panels[0].slug).toBe('live-panel')
  })
})
