import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  extractPaperVariants,
  getPaperProcessingDisclosure,
  isMockResponse,
  PaperRequestError,
} from '@/lib/paperVariants'

const EMPTY_RESPONSE = {
  mode: 'paper_variants_extract',
  generated_at: '2026-07-19T00:00:00Z',
  llm_provider: 'mock',
  pdf: null,
  source_metadata: null,
  guardrails: {
    patient_data: 'not_requested',
    raw_paper_text_in_output: 'blocked',
    secrets_in_output: 'blocked',
  },
  candidate_count: 0,
  validated_count: 0,
  variants: [],
  warnings: [],
  provenance: ['deterministic_local_extractor'],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('extractPaperVariants', () => {
  it('fails before fetch when no bearer token is available', async () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)

    await expect(extractPaperVariants({ text: 'RPE65 c.260A>G' })).rejects.toMatchObject({
      code: 'auth_required',
    })
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('attaches the current bearer token to JSON extraction', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(EMPTY_RESPONSE), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchSpy)

    await extractPaperVariants(
      { text: 'RPE65 c.260A>G' },
      { accessToken: 'session-token' },
    )

    expect(fetchSpy).toHaveBeenCalledOnce()
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(init.headers).toEqual({
      'Content-Type': 'application/json',
      Authorization: 'Bearer session-token',
    })
    expect(init.body).toBe(JSON.stringify({ text: 'RPE65 c.260A>G' }))
  })

  it('attaches bearer auth to PDF multipart without overriding its boundary', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(EMPTY_RESPONSE), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchSpy)
    const pdf = new File(['%PDF-1.7'], 'paper.pdf', { type: 'application/pdf' })

    await extractPaperVariants({ pdf }, { accessToken: 'session-token' })

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(init.headers).toEqual({ Authorization: 'Bearer session-token' })
    expect(init.body).toBeInstanceOf(FormData)
  })

  it('fetches the server-issued processing disclosure before upload', async () => {
    const disclosure = {
      execution: 'external_provider',
      provider_id: 'gateway',
      provider_label: 'Approved AI gateway',
      input_classes: ['paper_text'],
      raw_input_persisted: false,
      retention: 'request_lifetime',
      expires_at: null,
      user_deletable: false,
      consent_required: true,
      warnings: [],
    }
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(disclosure), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchSpy)

    await expect(
      getPaperProcessingDisclosure('paper_text', { accessToken: 'session-token' }),
    ).resolves.toEqual(disclosure)
    expect(fetchSpy.mock.calls[0]?.[0]).toBe(
      '/api/v1/paper-variants/disclosure?input_class=paper_text',
    )
    expect((fetchSpy.mock.calls[0]?.[1] as RequestInit).headers).toEqual({
      Authorization: 'Bearer session-token',
    })
  })

  it('sends the processing-consent receipt only after explicit acceptance', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(EMPTY_RESPONSE), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchSpy)

    await extractPaperVariants(
      { text: 'RPE65 c.260A>G' },
      { accessToken: 'session-token', processingConsent: true },
    )

    expect((fetchSpy.mock.calls[0]?.[1] as RequestInit).headers).toEqual({
      'Content-Type': 'application/json',
      Authorization: 'Bearer session-token',
      'X-Eamos-Processing-Consent': 'true',
    })
  })

  it('does not expose backend JSON in an auth failure', async () => {
    const raw = JSON.stringify({ detail: 'Not authenticated', internal: 'request-body-fragment' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(raw, { status: 401 })))

    const error = await extractPaperVariants(
      { text: 'private publication text' },
      { accessToken: 'expired-token' },
    ).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(PaperRequestError)
    expect(error).toMatchObject({ code: 'auth_expired', status: 401 })
    expect(String(error)).not.toContain('Not authenticated')
    expect(String(error)).not.toContain('request-body-fragment')
  })

  it('treats an unreachable backend as unavailable, never as fixture data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))

    await expect(
      extractPaperVariants({ text: 'RPE65 c.260A>G' }, { accessToken: 'session-token' }),
    ).rejects.toMatchObject({ code: 'unavailable' })
  })

  it('uses fixture output only when explicitly requested', async () => {
    const response = await extractPaperVariants(
      { text: 'fixture input', sourceName: 'Smith2021.txt' },
      { fixture: true },
    )

    expect(isMockResponse(response)).toBe(true)
  })
})
