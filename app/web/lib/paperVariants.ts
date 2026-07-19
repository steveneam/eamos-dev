import type {
  PaperSourceMetadata,
  PaperVariantsResponse,
  ProcessingDisclosureV1,
  SearchInputCandidate,
  ValidatedPaperVariant,
  WorkflowRunV1,
} from './backend'

// Paper → variants client. next.config.ts rewrites `/api/*` to FastAPI in
// local development. Set NEXT_PUBLIC_API_BASE_URL to an absolute origin to call
// a remote backend.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? ''

export interface PaperExtractInput {
  /** Pasted text or the contents of an uploaded .txt. */
  text?: string
  /** A PDF to send multipart; the backend extracts text via pdf_text. */
  pdf?: File | null
  /** FE orchestration hint (filename/source label). Ignored by the live endpoint
   *  (which derives metadata from content); only the .eamos-mock path uses it to
   *  synthesize illustrative per-source bibliographic metadata. */
  sourceName?: string
}

export type PaperRequestErrorCode =
  | 'auth_required'
  | 'auth_expired'
  | 'consent_required'
  | 'validation'
  | 'rate_limited'
  | 'timeout'
  | 'unavailable'
  | 'request_failed'

/**
 * Safe, presentation-ready failure from the Paper API boundary. Response
 * bodies are deliberately not copied into this error: they can contain
 * validation internals, request fragments, or framework JSON that does not
 * belong in the product surface.
 */
export class PaperRequestError extends Error {
  readonly code: PaperRequestErrorCode
  readonly status?: number

  constructor(message: string, options: { code: PaperRequestErrorCode; status?: number }) {
    super(message)
    this.name = 'PaperRequestError'
    this.code = options.code
    this.status = options.status
    Object.setPrototypeOf(this, PaperRequestError.prototype)
  }
}

export interface PaperExtractOptions {
  signal?: AbortSignal
  /** Current verified Supabase session token. Never place it in a URL or log. */
  accessToken?: string | null
  /** Explicit fixture mode for local demos/tests. Network failures never enable it. */
  fixture?: boolean
  /** Sent only after the user accepts the server-issued disclosure. */
  processingConsent?: boolean
  /** Receives the safe opaque run id returned in the response header. */
  onWorkflowRunId?: (runId: string) => void
}

export type PaperInputClass = 'paper_text' | 'pdf'

export interface PaperRunPage {
  runs: WorkflowRunV1[]
  nextCursor: string | null
  total: number | null
}

const OPAQUE_RUN_ID = /^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$/

/** True when the response came from the local .eamos-mock fixture rather than a
 *  live extraction — drives the "Mock" marker on the surface. */
export function isMockResponse(res: PaperVariantsResponse): boolean {
  return res.provenance.includes(MOCK_PROVENANCE)
}

export async function extractPaperVariants(
  input: PaperExtractInput,
  options: PaperExtractOptions = {},
): Promise<PaperVariantsResponse> {
  if (options.fixture) return mockResponse(input)

  const token = options.accessToken?.trim()
  if (!token) {
    throw new PaperRequestError('Sign in before extracting variants from a publication.', {
      code: 'auth_required',
    })
  }

  try {
    let response: Response
    if (input.pdf) {
      const form = new FormData()
      form.append('pdf', input.pdf)
      response = await fetch(`${API_BASE_URL}/api/v1/paper-variants/extract`, {
        method: 'POST',
        headers: paperHeaders(token, options.processingConsent),
        body: form,
        signal: options.signal,
      })
    } else {
      response = await fetch(`${API_BASE_URL}/api/v1/paper-variants/extract`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...paperHeaders(token, options.processingConsent),
        },
        body: JSON.stringify({ text: input.text ?? '' }),
        signal: options.signal,
      })
    }
    if (!response.ok) {
      throw paperErrorForStatus(response.status)
    }
    const runId = response.headers.get('X-Workflow-Run-Id')?.trim()
    if (runId && OPAQUE_RUN_ID.test(runId)) options.onWorkflowRunId?.(runId)
    return (await response.json()) as PaperVariantsResponse
  } catch (err) {
    if (err instanceof PaperRequestError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    if (err instanceof TypeError) {
      throw new PaperRequestError(
        'Paper extraction is unavailable. Check your connection, then try again.',
        { code: 'unavailable' },
      )
    }
    throw err
  }
}

export async function listPaperRuns(
  options: Pick<PaperExtractOptions, 'accessToken' | 'signal'> & {
    limit?: number
    cursor?: string | null
  },
): Promise<PaperRunPage> {
  const params = new URLSearchParams({ limit: String(options.limit ?? 20) })
  if (options.cursor) params.set('cursor', options.cursor)
  const response = await paperFetch(`/api/v1/paper-variants/runs?${params.toString()}`, options)
  const runs = (await response.json()) as WorkflowRunV1[]
  const totalHeader = response.headers.get('X-Total-Count')
  const parsedTotal = totalHeader == null ? null : Number.parseInt(totalHeader, 10)
  return {
    runs,
    nextCursor: response.headers.get('X-Next-Cursor'),
    total: parsedTotal != null && Number.isFinite(parsedTotal) ? parsedTotal : null,
  }
}

export async function getPaperRun(
  runId: string,
  options: Pick<PaperExtractOptions, 'accessToken' | 'signal'>,
): Promise<WorkflowRunV1> {
  const response = await paperFetch(
    `/api/v1/paper-variants/runs/${encodeRunId(runId)}`,
    options,
  )
  return (await response.json()) as WorkflowRunV1
}

export async function getPaperRunResult(
  runId: string,
  options: Pick<PaperExtractOptions, 'accessToken' | 'signal'>,
): Promise<PaperVariantsResponse> {
  const response = await paperFetch(
    `/api/v1/paper-variants/runs/${encodeRunId(runId)}/result`,
    options,
  )
  return (await response.json()) as PaperVariantsResponse
}

export async function cancelPaperRun(
  runId: string,
  options: Pick<PaperExtractOptions, 'accessToken' | 'signal'>,
): Promise<WorkflowRunV1> {
  const response = await paperFetch(
    `/api/v1/paper-variants/runs/${encodeRunId(runId)}/cancel`,
    options,
    { method: 'POST' },
  )
  return (await response.json()) as WorkflowRunV1
}

export async function deletePaperRun(
  runId: string,
  options: Pick<PaperExtractOptions, 'accessToken' | 'signal'>,
): Promise<void> {
  await paperFetch(`/api/v1/paper-variants/runs/${encodeRunId(runId)}`, options, {
    method: 'DELETE',
  })
}

/**
 * Fetch the server-authoritative processing posture before any publication
 * body is uploaded. Provider choice is derived from trusted server settings;
 * the browser supplies only the bounded input class.
 */
export async function getPaperProcessingDisclosure(
  inputClass: PaperInputClass,
  options: Pick<PaperExtractOptions, 'accessToken' | 'signal'> = {},
): Promise<ProcessingDisclosureV1> {
  const token = options.accessToken?.trim()
  if (!token) {
    throw new PaperRequestError('Sign in before extracting variants from a publication.', {
      code: 'auth_required',
    })
  }
  try {
    const params = new URLSearchParams({ input_class: inputClass })
    const response = await fetch(
      `${API_BASE_URL}/api/v1/paper-variants/disclosure?${params.toString()}`,
      { headers: paperHeaders(token), signal: options.signal },
    )
    if (!response.ok) throw paperErrorForStatus(response.status)
    return (await response.json()) as ProcessingDisclosureV1
  } catch (err) {
    if (err instanceof PaperRequestError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    if (err instanceof TypeError) {
      throw new PaperRequestError(
        'Processing details are unavailable. Check your connection, then try again.',
        { code: 'unavailable' },
      )
    }
    throw err
  }
}

async function paperFetch(
  path: string,
  options: Pick<PaperExtractOptions, 'accessToken' | 'signal'>,
  init: RequestInit = {},
): Promise<Response> {
  const token = options.accessToken?.trim()
  if (!token) {
    throw new PaperRequestError('Sign in before opening a saved Paper run.', {
      code: 'auth_required',
    })
  }
  try {
    const headers = new Headers(init.headers)
    headers.set('Authorization', `Bearer ${token}`)
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: options.signal,
    })
    if (!response.ok) throw paperErrorForStatus(response.status)
    return response
  } catch (err) {
    if (err instanceof PaperRequestError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    if (err instanceof TypeError) {
      throw new PaperRequestError('Saved Paper runs are unavailable. Check your connection.', {
        code: 'unavailable',
      })
    }
    throw err
  }
}

function encodeRunId(runId: string): string {
  const normalized = runId.trim()
  if (!OPAQUE_RUN_ID.test(normalized)) {
    throw new PaperRequestError('This Paper run link is invalid.', { code: 'validation' })
  }
  return encodeURIComponent(normalized)
}

function paperHeaders(token: string, processingConsent = false): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    ...(processingConsent ? { 'X-Eamos-Processing-Consent': 'true' } : {}),
  }
}

function paperErrorForStatus(status: number): PaperRequestError {
  if (status === 401) {
    return new PaperRequestError('Your session expired. Sign in again to continue.', {
      code: 'auth_expired',
      status,
    })
  }
  if (status === 428) {
    return new PaperRequestError('Review and accept the processing details before continuing.', {
      code: 'consent_required',
      status,
    })
  }
  if (status === 400 || status === 413 || status === 415 || status === 422) {
    return new PaperRequestError(
      status === 413
        ? 'This publication exceeds the upload limit.'
        : 'Eamos could not accept this publication. Check the file or pasted text, then retry.',
      { code: 'validation', status },
    )
  }
  if (status === 429) {
    return new PaperRequestError('Paper extraction is temporarily rate limited. Wait, then retry.', {
      code: 'rate_limited',
      status,
    })
  }
  if (status === 504) {
    return new PaperRequestError('Paper extraction timed out. Retry this source.', {
      code: 'timeout',
      status,
    })
  }
  if (status === 404 || status === 501 || status === 503) {
    return new PaperRequestError('Paper extraction is unavailable in this environment.', {
      code: 'unavailable',
      status,
    })
  }
  return new PaperRequestError('Paper extraction failed. Retry this source.', {
    code: 'request_failed',
    status,
  })
}

// ─── .eamos-mock fixture ────────────────────────────────────────────────
// Mirrors the eamos_paper_variants CLI report dict and exercises every
// fail-closed state the UI must render: a validated clinical allele (✓), an
// ambiguous protein mention with multiple source-backed candidates (⚠), an
// experimental construct (⌀), and an unresolved cDNA (held). The genomic
// coordinates here are illustrative — "validated" means resolved-to-coordinates,
// NOT a pathogenicity claim; Open report loads the real (live) classification.

const MOCK_PROVENANCE = 'mock_paper_variants_extractor'

function mockCandidate(partial: Partial<SearchInputCandidate> & { candidate_id: string; gene: string }): SearchInputCandidate {
  return {
    display_label: partial.display_label ?? partial.gene,
    match_reason: partial.match_reason ?? 'source_backed',
    source_support: partial.source_support ?? [],
    source_count: partial.source_count ?? (partial.source_support?.length ?? 0),
    confidence: partial.confidence ?? 'medium',
    warnings: partial.warnings ?? [],
    cdna: partial.cdna ?? null,
    transcript: partial.transcript ?? null,
    protein_change: partial.protein_change ?? null,
    genomic_hg38: partial.genomic_hg38 ?? null,
    genomic_hgvs: partial.genomic_hgvs ?? null,
    distance: partial.distance ?? null,
    ...partial,
  }
}

const MOCK_VARIANTS: ValidatedPaperVariant[] = [
  {
    // ✓ Validated clinical allele — gets Open report + Library.
    gene: 'RPE65',
    transcript_hgvs: 'NM_000329.3:c.260A>G',
    protein_change: 'p.Asp87Gly',
    protein_hgvs: 'p.(Asp87Gly)',
    level: 'cdna',
    context: 'clinical_allele',
    evidence_quote:
      'The proband was homozygous for the RPE65 c.260A>G allele, which segregated with early-onset retinal dystrophy in the family.',
    validated: true,
    validation_status: 'resolved',
    variant_id: '1-68429683-A-G',
    genomic_hgvs: 'NC_000001.11:g.68429683A>G',
    resolved_candidate_id: 'rpe65-c260ag',
    source_support: ['VariantValidator', 'ClinVar'],
    source_inputs: {
      variant_validator: 'NM_000329.3:c.260A>G',
      ensembl_vep: null,
      gnomad: '1-68429683-A-G',
      spliceai: null,
      clinvar: 'VCV000098901',
      literature_terms: ['RPE65', 'Leber congenital amaurosis'],
    },
    candidates: [
      mockCandidate({
        candidate_id: 'rpe65-c260ag',
        display_label: 'RPE65 c.260A>G',
        gene: 'RPE65',
        cdna: 'c.260A>G',
        transcript: 'NM_000329.3',
        protein_change: 'p.(Asp87Gly)',
        genomic_hg38: '1-68429683-A-G',
        genomic_hgvs: 'NC_000001.11:g.68429683A>G',
        match_reason: 'exact_source_match',
        source_support: ['VariantValidator', 'ClinVar'],
        source_count: 2,
        confidence: 'high',
      }),
    ],
    resolver_warnings: [],
    resolver_provenance: ['eamos_search_input_resolver', 'search_candidate_resolver'],
  },
  {
    // ⚠ Ambiguous protein mention — multiple source-backed transcripts, no
    // clinical action until one is chosen (renders the <CandidateCard> chooser).
    gene: 'ABCA4',
    transcript_hgvs: null,
    protein_change: 'p.Gly1961Glu',
    protein_hgvs: 'p.(Gly1961Glu)',
    level: 'protein',
    context: 'clinical_allele',
    evidence_quote:
      'Two patients carried the recurrent ABCA4 p.Gly1961Glu missense change in trans with a null allele.',
    validated: false,
    validation_status: 'candidates',
    variant_id: null,
    genomic_hgvs: null,
    resolved_candidate_id: null,
    source_support: ['VariantValidator'],
    source_inputs: {
      variant_validator: 'ABCA4 p.Gly1961Glu',
      ensembl_vep: null,
      gnomad: null,
      spliceai: null,
      clinvar: null,
      literature_terms: ['ABCA4', 'Stargardt disease'],
    },
    candidates: [
      mockCandidate({
        candidate_id: 'abca4-g1961e-nm000350',
        display_label: 'ABCA4 c.5882G>A',
        gene: 'ABCA4',
        cdna: 'c.5882G>A',
        transcript: 'NM_000350.3',
        protein_change: 'p.(Gly1961Glu)',
        genomic_hg38: '1-94002359-C-T',
        match_reason: 'protein_to_cdna',
        source_support: ['VariantValidator', 'ClinVar'],
        source_count: 2,
        confidence: 'medium',
      }),
      mockCandidate({
        candidate_id: 'abca4-g1961e-alt',
        display_label: 'ABCA4 c.5882G>A (alt transcript)',
        gene: 'ABCA4',
        cdna: 'c.5882G>A',
        transcript: 'NM_001425303.1',
        protein_change: 'p.(Gly1961Glu)',
        match_reason: 'protein_to_cdna',
        source_support: ['VariantValidator'],
        source_count: 1,
        confidence: 'medium',
      }),
    ],
    resolver_warnings: ['multiple transcripts resolve this protein change'],
    resolver_provenance: ['eamos_search_input_resolver', 'search_candidate_resolver'],
  },
  {
    // ⌀ Experimental construct — non-clinical. Stays fail-closed even though the
    // protein→cDNA resolver returns same-residue recommendations: these render
    // read-only ("Recommended cDNA · research only"), never a clinical action.
    gene: 'RPE65',
    transcript_hgvs: null,
    protein_change: 'p.His241Ala',
    protein_hgvs: 'p.(His241Ala)',
    level: 'protein',
    context: 'experimental_construct',
    evidence_quote:
      'We engineered the RPE65 p.His241Ala substitution by site-directed mutagenesis to probe the isomerohydrolase active site.',
    validated: false,
    validation_status: 'experimental_construct',
    variant_id: null,
    genomic_hgvs: null,
    resolved_candidate_id: null,
    source_support: [],
    source_inputs: null,
    candidates: [
      mockCandidate({
        candidate_id: 'rpe65-h241a-rec1',
        display_label: 'RPE65 c.721C>G',
        gene: 'RPE65',
        cdna: 'c.721C>G',
        transcript: 'NM_000329.3',
        protein_change: 'p.(His241Ala)',
        match_reason: 'same_residue_recommendation',
        source_support: ['ClinVar'],
        source_count: 1,
        confidence: 'medium',
      }),
      mockCandidate({
        candidate_id: 'rpe65-h241a-rec2',
        display_label: 'RPE65 c.722A>C',
        gene: 'RPE65',
        cdna: 'c.722A>C',
        transcript: 'NM_000329.3',
        protein_change: 'p.(His241Ala)',
        match_reason: 'same_residue_recommendation',
        source_support: ['ClinGen'],
        source_count: 1,
        confidence: 'medium',
      }),
    ],
    resolver_warnings: ['experimental construct — cDNA suggestions are research-only, not clinical'],
    resolver_provenance: ['eamos_search_input_resolver', 'search_candidate_resolver'],
  },
  {
    // ⊘ Held — a cDNA mention that did not resolve to coordinates.
    gene: 'CRB1',
    transcript_hgvs: 'c.2843G>A',
    protein_change: null,
    protein_hgvs: null,
    level: 'cdna',
    context: 'clinical_allele',
    evidence_quote: 'A CRB1 c.2843G>A variant was reported in one affected sibling.',
    validated: false,
    validation_status: 'missing',
    variant_id: null,
    genomic_hgvs: null,
    resolved_candidate_id: null,
    source_support: [],
    source_inputs: null,
    candidates: [],
    resolver_warnings: ['no transcript context — could not anchor coordinates'],
    resolver_provenance: ['eamos_search_input_resolver'],
  },
]

// Synthesize illustrative bibliographic metadata from an "Author+Year" filename
// (e.g. "Smith2021.txt"). Returns null for unrecognised names / pasted text, so
// the FE falls back to the filename citation — matching live behaviour for a
// source with no extractable metadata.
function mockSourceMetadata(name?: string): PaperSourceMetadata | null {
  if (!name) return null
  const base = name.replace(/\.[^.]+$/, '')
  const m = base.match(/^([A-Za-z][A-Za-z'-]+)[ _-]?(\d{4})\b/)
  if (!m) return null
  const author = m[1]
  const year = m[2]
  return {
    title: `Variant findings in inherited retinal disease (${author} cohort)`,
    authors: [`${author} J`, 'Nguyen T', 'Okafor C'],
    year,
    journal: 'Mock J. Med. Genet.',
    doi: `10.1000/mock.${year}.${author.toLowerCase()}`,
    pmid: String(30000000 + Number(year) * 100 + base.length),
  }
}

function mockResponse(input: PaperExtractInput): PaperVariantsResponse {
  const validated = MOCK_VARIANTS.filter((v) => v.validated).length
  return {
    mode: 'paper_variants_extract',
    // Fixed stamp — Date.now() is intentionally avoided so the fixture is
    // deterministic across renders/tests.
    generated_at: '2026-06-14T00:00:00+00:00',
    llm_provider: 'mock',
    pdf: input.pdf
      ? { page_count: 12, engine: 'pypdf', warnings: ['scanned-page text layer is sparse'] }
      : null,
    // Illustrative per-source bibliographic metadata so the By-paper header can
    // demonstrate title/authors/PMID. Live, Codex populates this from PDF
    // metadata / first-page parse; a real text source with no metadata returns
    // null and the FE falls back to the filename citation.
    source_metadata: mockSourceMetadata(input.sourceName),
    guardrails: {
      patient_data: 'not_used',
      raw_paper_text_in_output: 'blocked',
      secrets_in_output: 'blocked',
    },
    candidate_count: MOCK_VARIANTS.length,
    validated_count: validated,
    variants: MOCK_VARIANTS,
    warnings: [],
    provenance: [MOCK_PROVENANCE],
  }
}
