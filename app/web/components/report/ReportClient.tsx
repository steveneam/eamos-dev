'use client'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { WorkRail } from '@/components/layout/WorkRail'
import { RailFoot } from '@/components/layout/RailFoot'
import { VariantLibraryRail } from '@/components/report/VariantLibraryRail'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { VariantHeader } from '@/components/report/VariantHeader'
import { VariantDecoder } from '@/components/report/VariantDecoder'
import { AIStack } from '@/components/aistack/AIStack'
import { ClinVarBlock } from '@/components/report/ClinVarBlock'
import { DiseaseSection } from '@/components/report/DiseaseSection'
import { TrialsSection } from '@/components/report/TrialsSection'
import { PubMedSection } from '@/components/report/PubMedSection'
import { LazySection } from '@/components/report/LazySection'
import { CalibratedInSilicoTable } from '@/components/report/CalibratedInSilicoTable'
import { CompositeVerdictBar } from '@/components/report/CompositeVerdictBar'
import { AcmgCriteriaFold } from '@/components/report/AcmgCriteriaFold'
import { CuratedVariantsGrid } from '@/components/report/CuratedVariantsGrid'
import { AssociatedConditions } from '@/components/report/AssociatedConditions'
import { PopulationFrequencySection } from '@/components/report/PopulationFrequencySection'
import { AfThermometer } from '@/components/report/AfThermometer'
import { EamosAcmgClassifier } from '@/components/report/EamosAcmgClassifier'
import { LossOfFunctionBlock } from '@/components/report/LossOfFunctionBlock'
import { MaveFunctionalBlock } from '@/components/report/MaveFunctionalBlock'
import { CallCardsGrid } from '@/components/report/CallCardsGrid'
import { AdvisorySummaryStrip } from '@/components/report/AdvisorySummaryStrip'
import { classificationToTier, mockEamosComputed } from '@/lib/acmg/mock'
import { ReportLoadingState } from '@/components/report/ReportLoadingState'
import { ExportMenu } from '@/components/report/ExportMenu'
import { SearchInterpretationPanel } from '@/components/report/SearchInterpretationPanel'
import { ReportGeneViewer } from '@/components/report/ReportGeneViewer'
import { StickyVariantRibbon } from '@/components/report/StickyVariantRibbon'
import { ExpertPanelSection } from '@/components/report/ExpertPanelSection'
import { MolecularContextBlock } from '@/components/report/MolecularContextBlock'
import { GeneDiseaseBlock } from '@/components/report/GeneDiseaseBlock'
import { Card, type Verdict } from '@/components/ui/Card'
import { CopyButton } from '@/components/ui/CopyButton'
import { variantLookup } from '@/lib/api'
import { cleanQuery, isLikelyUnparseable } from '@/lib/variant-format'
import { reportHrefForQuery } from '@/lib/variant-search'
import { RPE65_NEGATIVE_CONTROL_SAMPLE } from '@/lib/sample-report'
import {
  tsvDiseaseAndConditions,
  tsvEvidenceBySource,
  tsvGeneContextSnapshot,
  tsvPopulation,
  tsvPublications,
  tsvTrials,
} from '@/lib/report-tsv'
import {
  htmlDiseaseAndConditions,
  htmlEvidenceBySource,
  htmlGeneContextSnapshot,
  htmlPopulation,
  htmlPublications,
  htmlTrials,
} from '@/lib/report-html'
import type {
  ComputationalDeepDiveSection,
  ExpertPanelSection as ExpertPanelSectionData,
  LookupRequest,
  LookupResponse,
  LookupSectionId,
  PublicationLiterature,
  SearchInputCandidate,
  SearchInputInterpretation,
} from '@/lib/backend'

// LazySection lazy-branch hatch: section IDs that ReportBody will treat as
// `eagerData={null}` even when the payload ships them inline. Fixture mode
// synthesises a `summaryRequest` from `payload.report_profile.header` so the
// lazy fetch actually hits `/api/v1/lookup/sections`. This is the M11/M-007
// contract canary — same in dev and prod.
const LAZY_OVERRIDE_VALID_IDS: readonly LookupSectionId[] = [
  'publications',
  'computational_deep_dive',
  'clingen_vcep',
]

// Rendered for §3 when the live `clingen_vcep` section resolves to a non-
// `available` status (today's default is `partial`: a consensus-derived
// fallback, since the ClinGen Evidence-Repository source-cache isn't wired
// yet — Codex C1). An honest provenance note, not an error (role="note").
function ExpertPanelPartialNote() {
  return (
    <div
      role="note"
      style={{
        marginTop: 18,
        padding: '12px 14px',
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 'var(--r-md)',
        fontSize: 12,
        lineHeight: 1.5,
        color: 'var(--ink-3)',
      }}
    >
      Expert-panel classification is derived from the current clinical-consensus
      snapshot, not the ClinGen Evidence Repository. Full VCEP attribution lands
      when the Evidence-Repository source-cache is integrated.
    </div>
  )
}

function parseLazyOverrides(raw: string | null): Set<LookupSectionId> {
  const out = new Set<LookupSectionId>()
  if (!raw) return out
  for (const token of raw.split(',').map((s) => s.trim()).filter(Boolean)) {
    if ((LAZY_OVERRIDE_VALID_IDS as readonly string[]).includes(token)) {
      out.add(token as LookupSectionId)
    }
  }
  return out
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading'; requestKey: string }
  | { kind: 'ready'; requestKey: string; data: LookupResponse }
  | { kind: 'malformed'; requestKey: string; query: string; detail?: string }
  | { kind: 'unresolved'; requestKey: string; query: string }
  | {
      kind: 'interpretation'
      requestKey: string
      query: string
      interpretation: SearchInputInterpretation
      detail?: string | null
    }
  | { kind: 'error'; requestKey: string; message: string }
  | { kind: 'offline'; requestKey: string }

const REPORT_CACHE_PREFIX = 'eamos.report.lookup.v1:'
const REPORT_CACHE_MAX_AGE_MS = 30 * 60 * 1000
const LIVE_SAMPLE_REPORT_HREF = '/report?gene=USH2A&cdna=c.2276G%3ET'

function reportRequestKey({
  cdna,
  demo,
  fixture,
  gene,
  proteinChange,
  q,
  transcript,
}: {
  cdna: string
  demo: boolean
  fixture: boolean
  gene: string
  proteinChange: string
  q: string
  transcript: string
}) {
  if (fixture) return 'fixture:rpe65-negative'
  if (demo) return 'demo:live-redirect'
  if (!gene && !cdna && q) return `q:${q}`
  if (gene || cdna) {
    return ['lookup', gene.toUpperCase(), cleanQuery(cdna), transcript, proteinChange].join('|')
  }
  return 'empty'
}

function isAbortError(err: unknown) {
  return err instanceof Error && err.name === 'AbortError'
}

function readCachedReport(requestKey: string): LookupResponse | null {
  if (
    typeof window === 'undefined' ||
    requestKey === 'empty' ||
    requestKey.startsWith('demo:') ||
    requestKey.startsWith('fixture:')
  ) {
    return null
  }
  const key = `${REPORT_CACHE_PREFIX}${requestKey}`
  try {
    const raw = window.sessionStorage.getItem(key)
    if (!raw) return null
    const cached = JSON.parse(raw) as { savedAt?: unknown; data?: unknown }
    if (typeof cached.savedAt !== 'number' || !cached.data) {
      window.sessionStorage.removeItem(key)
      return null
    }
    if (Date.now() - cached.savedAt > REPORT_CACHE_MAX_AGE_MS) {
      window.sessionStorage.removeItem(key)
      return null
    }
    return cached.data as LookupResponse
  } catch {
    try {
      window.sessionStorage.removeItem(key)
    } catch {
      // Ignore storage APIs that are unavailable in private contexts.
    }
    return null
  }
}

function writeCachedReport(requestKey: string, data: LookupResponse) {
  if (
    typeof window === 'undefined' ||
    requestKey === 'empty' ||
    requestKey.startsWith('demo:') ||
    requestKey.startsWith('fixture:')
  ) {
    return
  }
  try {
    window.sessionStorage.setItem(
      `${REPORT_CACHE_PREFIX}${requestKey}`,
      JSON.stringify({ savedAt: Date.now(), data }),
    )
  } catch {
    // Quota/private-mode failures should never block rendering the report.
  }
}

export function ReportClient() {
  const params = useSearchParams()
  const router = useRouter()
  const gene = params.get('gene')?.trim() ?? ''
  const cdna = params.get('cdna')?.trim() ?? ''
  const transcript = params.get('transcript')?.trim() ?? ''
  const proteinChange = params.get('protein_change')?.trim() ?? ''
  const q = params.get('q')?.trim() ?? ''
  const demo = params.get('demo') !== null
  const fromCompare = params.get('from') === 'compare'
  const backHref = fromCompare ? '/compare' : '/'
  const backLabel = fromCompare ? 'Back to filters' : 'Back to search'
  const negativeFixture = params.get('fixture') === 'rpe65-negative'
  const lazyParam = params.get('lazy')
  const lazyOverrides = useMemo(() => parseLazyOverrides(lazyParam), [lazyParam])
  const requestKey = useMemo(
    () => reportRequestKey({ cdna, demo, fixture: negativeFixture, gene, proteinChange, q, transcript }),
    [cdna, demo, negativeFixture, gene, proteinChange, q, transcript],
  )

  const [state, setState] = useState<LoadState>({ kind: 'idle' })
  const [attempt, setAttempt] = useState(0)
  // Focus-expand: the compact search grows from a narrower resting width to fill
  // the bar when focused — on desktop AND mobile. Percentage width gives a smooth
  // %→% transition (no px overshoot/snap) at any viewport.
  const [searchFocused, setSearchFocused] = useState(false)

  // M7 live-wire: mirror the LookupRequest the report itself uses so the
  // MatrixOverture can call lookupSummary() and upgrade its mock tiles.
  // Redirect and fixture modes leave request undefined so no live lookup runs.
  const summaryRequest = useMemo<LookupRequest | undefined>(() => {
    if (demo || negativeFixture) return undefined
    if (!gene && !cdna && q) {
      return { search_text: q, species: 'human' }
    }
    if (gene && cdna) {
      return {
        gene,
        cdna: cleanQuery(cdna),
        transcript: transcript || null,
        protein_change: proteinChange || null,
        species: 'human',
      }
    }
    return undefined
  }, [demo, negativeFixture, gene, cdna, transcript, proteinChange, q])

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    if (demo) {
      router.replace(LIVE_SAMPLE_REPORT_HREF)
      return () => controller.abort()
    }

    if (negativeFixture) {
      return () => controller.abort()
    }

    if (!gene && !cdna && !q) {
      router.replace(LIVE_SAMPLE_REPORT_HREF)
      return () => controller.abort()
    }

    if (!gene && !cdna && q) {
      // Raw searches resolve through the backend parser/candidate gate before
      // any report payload is rendered.
      const cachedData = readCachedReport(requestKey)
      if (cachedData) {
        void Promise.resolve().then(() => {
          if (!cancelled) setState({ kind: 'ready', requestKey, data: cachedData })
        })
      }
      variantLookup({ search_text: q, species: 'human' }, { signal: controller.signal })
        .then((data) => {
          if (cancelled) return
          const interpretation = data.search_interpretation ?? null
          const responseGene =
            data.report_payload.report_profile?.header?.gene ??
            data.report_payload.variant_summary_rows[0]?.gene
          if (interpretation && !responseGene) {
            setState({
              kind: 'interpretation',
              requestKey,
              query: q,
              interpretation,
              detail: data.report_payload.limitations,
            })
            return
          }
          if (responseGene && interpretation?.gene && responseGene.toUpperCase() !== interpretation.gene.toUpperCase()) {
            setState({
              kind: 'error',
              requestKey,
              message: `Lookup returned data for ${responseGene}, but the search resolved to ${interpretation.gene}. The report was not rendered to avoid showing stale variant facts.`,
            })
            return
          }
          writeCachedReport(requestKey, data)
          setState({ kind: 'ready', requestKey, data })
        })
        .catch((err: Error) => {
          if (cancelled || isAbortError(err)) return
          if (cachedData) return
          if (err instanceof TypeError) {
            setState({ kind: 'offline', requestKey })
          } else {
            setState({ kind: 'error', requestKey, message: err.message })
          }
        })
      return () => {
        cancelled = true
        controller.abort()
      }
    }

    if (!gene || !cdna) {
      void Promise.resolve().then(() => {
        if (!cancelled) {
          setState({
            kind: 'error',
            requestKey,
            message: 'Both a gene and a cDNA (or HGVS) change are required.',
          })
        }
      })
      return () => controller.abort()
    }

    // BE-8 mirror: clean before building the request (never lowercases HGVS).
    const cleanedCdna = cleanQuery(cdna)
    const probe = `${gene.toUpperCase()} ${cleanedCdna}`.trim()

    // Client-side malformed guard — only short-circuit on input that's
    // unparseable every way (a lone rs…/p.…/coord is valid backend input and
    // must NOT be blocked here). The backend is authoritative and emits
    // `input_unparseable:<kind>` for the cases this guard lets through.
    if (isLikelyUnparseable(gene, cdna)) {
      void Promise.resolve().then(() => {
        if (!cancelled) setState({ kind: 'malformed', requestKey, query: probe })
      })
      return () => controller.abort()
    }

    const cachedData = readCachedReport(requestKey)
    if (cachedData) {
      void Promise.resolve().then(() => {
        if (!cancelled) setState({ kind: 'ready', requestKey, data: cachedData })
      })
    }
    variantLookup({
      gene,
      cdna: cleanedCdna,
      transcript: transcript || null,
      protein_change: proteinChange || null,
      species: 'human',
    }, { signal: controller.signal })
      .then((data) => {
        if (cancelled) return
        // BE-12 frozen warning codes — see plans/v2-backend.md.
        const warnings = data.warnings ?? []
        if (warnings.some((c) => c.startsWith('input_unparseable:'))) {
          setState({
            kind: 'malformed',
            requestKey,
            query: probe,
            detail: data.report_payload.limitations ?? undefined,
          })
          return
        }
        if (warnings.includes('no_genomic_resolution')) {
          setState({ kind: 'unresolved', requestKey, query: probe })
          return
        }
        const responseGene =
          data.report_payload.report_profile?.header?.gene ??
          data.report_payload.variant_summary_rows[0]?.gene
        if (responseGene && responseGene.toUpperCase() !== gene.toUpperCase()) {
          setState({
            kind: 'error',
            requestKey,
            message: `Lookup returned data for ${responseGene}, but the URL requested ${gene}. The report was not rendered to avoid showing stale variant facts.`,
          })
          return
        }
        writeCachedReport(requestKey, data)
        setState({ kind: 'ready', requestKey, data })
      })
      .catch((err: Error) => {
        if (cancelled || isAbortError(err)) return
        if (cachedData) return
        // fetch() throws TypeError for connection-refused / DNS / CORS — i.e.
        // the dev backend isn't running. 4xx/5xx responses come through
        // parseResponse as a plain Error and route to the generic branch.
        // (variantLookup already retried once with backoff for network/5xx.)
        if (err instanceof TypeError) {
          setState({ kind: 'offline', requestKey })
        } else {
          setState({ kind: 'error', requestKey, message: err.message })
        }
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [gene, cdna, transcript, proteinChange, q, demo, negativeFixture, attempt, router, requestKey])

  // Same freeform behaviour as the landing hero search (shared util): structured
  // "GENE c.…/p.…/rs…" → lookup; anything else → raw query for the resolver.
  const handleSearch = (raw: string) => {
    const href = reportHrefForQuery(raw)
    if (href) router.push(href)
  }

  const handleSelectCandidate = (candidate: SearchInputCandidate) => {
    if (!candidate.gene || !candidate.cdna) return
    const p = new URLSearchParams({ gene: candidate.gene, cdna: candidate.cdna })
    if (candidate.transcript) p.set('transcript', candidate.transcript)
    if (candidate.protein_change) p.set('protein_change', candidate.protein_change)
    router.push(`/report?${p.toString()}`)
  }

  const queryLabel = `${gene} ${cdna}`.trim() || q
  let activeState: LoadState = { kind: 'loading', requestKey }
  if (negativeFixture) {
    activeState = { kind: 'ready', requestKey, data: RPE65_NEGATIVE_CONTROL_SAMPLE }
  } else if (state.kind !== 'idle' && state.requestKey === requestKey) {
    activeState = state
  }

  return (
    <div style={{ background: 'var(--bg-soft)', minHeight: '100vh' }}>
      <TopNav right={<ModePill current="report" />}>
        {/* Sticky nav (via TopNav). The compact search expands to fill the bar
            when focused and collapses back on blur — mirrors the landing nav. */}
        <div
          className="mx-auto"
          onFocus={() => setSearchFocused(true)}
          onBlur={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setSearchFocused(false)
          }}
          style={{
            width: '100%',
            maxWidth: searchFocused ? 760 : 640,
            transition: 'max-width 460ms var(--ease-emphasized)',
          }}
        >
          <EamosSearch size="compact" tone="light" onSubmit={handleSearch} />
        </div>
      </TopNav>

      {activeState.kind === 'ready' ? (
        // Ready report → controls-left <WorkRail surface="report">: the variant
        // library rail sits flush-left, the --maxw-report-frame reading column
        // passes through as the centered output verbatim (reading room intact).
        <WorkRail
          surface="report"
          title="Library"
          aiTitle="Ask Eamos"
          foot={<RailFoot />}
          aiPanel={
            <ReportAiPanel
              data={activeState.data}
              queryFallback={`${gene} ${cdna}`.trim() || activeState.data.query}
            />
          }
          output={
            <CenteredMain bleed>
              <ReportBody
                key={activeState.requestKey}
                data={activeState.data}
                query={`${gene} ${cdna}`.trim() || activeState.data.query}
                summaryRequest={summaryRequest}
                lazyOverrides={lazyOverrides}
                demo={negativeFixture}
              />
            </CenteredMain>
          }
        >
          <VariantLibraryRail data={activeState.data} query={queryLabel} />
        </WorkRail>
      ) : (
        // Loading / error / offline / malformed / unresolved / interpretation:
        // full-width centered column, no rail (never a rail over a non-report).
        <CenteredMain>
          {activeState.kind === 'loading' && (
            <ReportLoadingState query={queryLabel} gene={gene} cdna={cdna} />
          )}
          {activeState.kind === 'error' && (
            <ErrorBlock
              variant="generic"
              message={activeState.message}
              query={queryLabel}
              onRetry={() => setAttempt((n) => n + 1)}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'offline' && (
            <ErrorBlock
              variant="offline"
              query={queryLabel}
              onRetry={() => setAttempt((n) => n + 1)}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'malformed' && (
            <MalformedBlock
              query={activeState.query}
              detail={activeState.detail}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'unresolved' && (
            <ErrorBlock
              variant="unresolved"
              query={activeState.query}
              onRetry={() => setAttempt((n) => n + 1)}
              backHref={backHref}
              backLabel={backLabel}
              showDemo={!fromCompare}
            />
          )}
          {activeState.kind === 'interpretation' && (
            <SearchInterpretationPanel
              query={activeState.query}
              interpretation={activeState.interpretation}
              limitations={activeState.detail}
              onSelectCandidate={handleSelectCandidate}
            />
          )}
        </CenteredMain>
      )}
    </div>
  )
}

/** The report's main column wrapper. Shared by every load state and the ready
 *  WorkRail output so the column geometry is defined in exactly one place.
 *  `bleed` (the ready report) runs full-width like the Workbench — the card
 *  grid uses the whole surface; the narrow centered frame is kept for the
 *  short-text load/error states, where a full-width message reads poorly. */
function CenteredMain({ children, bleed = false }: { children: ReactNode; bleed?: boolean }) {
  return (
    <main
      className={bleed ? undefined : 'mx-auto'}
      style={
        bleed
          ? { width: '100%', maxWidth: 'none', padding: '32px 24px 80px' }
          : { width: '100%', maxWidth: 'var(--maxw-report-frame)', padding: '32px 32px 80px' }
      }
    >
      {children}
    </main>
  )
}

/** The Ask-Eamos rail surface for a ready report (docs/ai-work-rail/spec.md). Mirrors
 *  ReportBody's context derivation so the rail's context chip matches the report. */
function ReportAiPanel({ data, queryFallback }: { data: LookupResponse; queryFallback: string }) {
  const payload = data.report_payload
  const row0 = payload.variant_summary_rows[0]
  const contextLabel =
    row0?.gene && row0?.protein_change ? `${row0.gene} ${row0.protein_change}` : queryFallback
  return <AIStack payload={payload} contextLabel={contextLabel} />
}

interface ReportBodyProps {
  data: LookupResponse
  query: string
  summaryRequest?: LookupRequest
  lazyOverrides: Set<LookupSectionId>
  /** Offline fixture mode (?fixture=rpe65-negative) — render the gene viewer from the bundled
   *  GENE_VIEWER_SAMPLE rather than fetching, matching the rest of the
   *  fixture report's offline behaviour. */
  demo?: boolean
}

function ReportBody({ data, query, summaryRequest, lazyOverrides, demo = false }: ReportBodyProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const payload = data.report_payload
  const row0 = payload.variant_summary_rows[0]
  const contextLabel =
    row0?.gene && row0?.protein_change
      ? `${row0.gene} ${row0.protein_change}`
      : query
  const geneContextMeta = row0?.gene
    ? [row0.gene, row0.transcript_hgvs].filter(Boolean).join(' · ')
    : query || 'Gene context'

  // Identity for keying the paginated sections (PubMed/Trials) so their local
  // expand/fetch state resets when the rendered variant changes.
  const header = payload.report_profile?.header
  const variantKey = header ? `${header.gene}|${header.cdna}` : query

  // Lazy-hatch synthesised request: if fixture mode (`summaryRequest` undefined)
  // but a `?lazy=` override is present, synthesise a request from the report's
  // own header so `<LazySection>` can fire its IntersectionObserver-driven
  // `/api/v1/lookup/sections` fetch against the live backend even from the
  // offline-sample path.
  // Manual deps are intentional (header fields drive the fallback request). The
  // React Compiler infers a narrower set and skips optimizing — advisory only.
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const effectiveSummaryRequest = useMemo<LookupRequest | undefined>(() => {
    if (summaryRequest) return summaryRequest
    if (lazyOverrides.size === 0) return undefined
    if (!header?.gene || !header?.cdna) return undefined
    return {
      gene: header.gene,
      cdna: header.cdna,
      transcript: header.transcript ?? null,
      protein_change: header.protein_change ?? null,
      species: 'human',
    }
  }, [
    summaryRequest,
    lazyOverrides,
    header?.gene,
    header?.cdna,
    header?.transcript,
    header?.protein_change,
  ])

  // Ribbon facts — header is the authoritative split; row0 carries the
  // already-formatted strings (transcript_hgvs is "NM_...:c.260A>G"; split off
  // the transcript so the ribbon can recombine).
  const ribbonGene = header?.gene ?? row0?.gene ?? undefined
  const transcriptHgvs = row0?.transcript_hgvs ?? null
  const ribbonTranscript = header?.transcript ?? transcriptHgvs?.split(':')[0] ?? undefined
  const ribbonHgvsC = header?.cdna ?? transcriptHgvs?.split(':')[1] ?? undefined
  const ribbonHgvsP = header?.protein_change ?? row0?.protein_change ?? undefined

  // Derive verdict for Card accent + (future) review stars from optional fields.
  const verdict = deriveClassificationVerdict(
    payload.report_profile?.header?.classification ??
      payload.report_profile?.acmg_worksheet?.classification ??
      payload.acmg_classification,
  )

  // Ribbon Share — mirrors the hero Share (copy link). Copy + Cite were removed
  // from the ribbon (Copy duplicates the per-section copy buttons; Cite lives in
  // the bottom-left dock).
  const handleShare = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(window.location.href)
    }
  }

  // BE-12 frozen code: any `live_fetch_failed:<ExceptionName>` means a source
  // fell back to cached data. Key on the prefix only — the suffix is the
  // exception class, not the tool name (incoherence finding #6). Non-blocking.
  const degraded = (data.warnings ?? []).some((c) => c.startsWith('live_fetch_failed:'))
  const targetFor = (sectionId: string) =>
    payload.report_profile?.extraction_plan?.section_targets.find(
      (target) => target.section_id === sectionId,
    ) ?? null
  const populationTarget = targetFor('population_frequency')
  const populationSection =
    populationTarget?.match_level === 'unavailable'
      ? null
      : payload.report_profile?.population_frequency
  const populationAf = populationSection?.overall?.total?.allele_frequency ?? null

  // EAMOS-computed ACMG/AMP advisory (points engine). The contract is frozen but
  // the engine does not populate the payload yet (Codex's report-population slice
  // is gated), so fall back to an illustrative mock — built to agree in direction
  // with the curated verdict so it never contradicts the precedence call — and
  // flag every instrument `.eamos-mock` until the live block lands. Mock-first,
  // same as §2 in-silico.
  const computedClassification =
    payload.eamos_computed_classification ?? mockEamosComputed(classificationToTier(verdict))
  const computedIsMock = !payload.eamos_computed_classification

  return (
    <div className="flex flex-col gap-3.5">
      {degraded && (
        <div
          role="status"
          style={{
            background: 'var(--bg-soft)',
            border: '0.5px solid var(--line)',
            borderRadius: 10,
            padding: '8px 14px',
            fontSize: 12,
            color: 'var(--ink-3)',
          }}
        >
          Some sources were temporarily unavailable and are showing the most
          recent cached data.
        </div>
      )}
      <StickyVariantRibbon
        gene={ribbonGene}
        transcript={ribbonTranscript}
        hgvsC={ribbonHgvsC}
        hgvsP={ribbonHgvsP}
        data={data}
        onShare={handleShare}
        exportSlot={<ExportMenu data={data} variant="ribbon" />}
      />
      <VariantHeader
        payload={payload}
        data={data}
        query={query}
        exportSlot={<ExportMenu data={data} variant="header" />}
      />

      <div className="flex flex-col gap-3.5">
        {/* Call cards sit just under the header as the at-a-glance verdicts.
            They're scannable summary; the numbered evidence sections begin
            below. */}
        <CallCardsGrid payload={payload} populationAf={populationAf} />

        {/* The glanceable EAMOS-computed advisory (Evidence Fingerprint + posterior
            chip), directly under the call cards. The full drawn decision (plane +
            waterfall + gauge) is the synthesis capstone of §2; this strip links
            down to it so the verdict is never buried. */}
        <AdvisorySummaryStrip
          payload={payload}
          computed={computedClassification}
          mock={computedIsMock}
          populationAf={populationAf}
        />

        {/* 1 · Clinical evidence — ClinGen expert panel + ClinVar + ACMG.
            ClinGen leads (highest weight for classification), then ClinVar,
            then the ACMG criteria fold. Leads the report (v3): the clinical
            classification is what a curator reads first. Verdict accent shows
            as the header leading dot (Card verdict prop). */}
        <div id="clinical_evidence" className="scroll-mt-24" />
        <Card
          number={1}
          title="Clinical evidence"
          meta="ClinGen · ClinVar · ACMG"
          verdict={verdict}
          actions={
            <CopyButton
              text={{
                html: htmlEvidenceBySource(
                  payload,
                  null,
                  payload.acmg_criteria_scaffold,
                  data.evidence
                    .filter((e) => e.source?.toLowerCase() === 'clinvar')
                    .map((e) => ({ source: e.source, status: e.status, summary: e.summary })),
                ),
                text: tsvEvidenceBySource(
                  payload,
                  null,
                  payload.acmg_criteria_scaffold,
                  data.evidence
                    .filter((e) => e.source?.toLowerCase() === 'clinvar')
                    .map((e) => ({ source: e.source, status: e.status, summary: e.summary })),
                ),
              }}
              label="Copy clinical evidence (paste into Excel for formatted table)"
            />
          }
        >
          <LazySection<ExpertPanelSectionData>
            key={`vcep-${variantKey}${lazyOverrides.has('clingen_vcep') ? '-lazy' : ''}`}
            eagerData={
              lazyOverrides.has('clingen_vcep')
                ? null
                : payload.report_profile?.expert_panel
            }
            sectionId="clingen_vcep"
            request={effectiveSummaryRequest ?? null}
            unwrap={(env) =>
              env.status === 'available' ? (env.payload as ExpertPanelSectionData | null) ?? null : null
            }
            forceLoad={lazyOverrides.has('clingen_vcep')}
            emptyView={<ExpertPanelPartialNote />}
            errorView={() => <ExpertPanelPartialNote />}
          >
            {(section) => <ExpertPanelSection data={section} />}
          </LazySection>
          <ClinVarBlock evidence={data.evidence} />
          {/* Functional evidence (PS3/BS3) from MaveDB — wet-lab MAVE/DMS assays;
              sits with the clinical evidence that drives the classification. */}
          <MaveFunctionalBlock gene={row0?.gene} query={query} />
          <AcmgCriteriaFold data={payload.acmg_criteria_scaffold} />
        </Card>

        {/* 2 · In-silico predictions — engines + calibrated buckets only.
            Verdict accent and ClinVar/ACMG live in §1 Clinical evidence;
            per-source data for variant_validator/gnomad/ensembl/spliceai/
            clingen/gene_disease/molecular_context/computational_annotations/
            pubmed/litvar2/clinical_trials/vep is rendered elsewhere or in the
            variant header. */}
        <div id="evidence_by_source" className="scroll-mt-24" />
        <Card
          number={2}
          title="In-silico predictions"
          meta="engines · calibrated"
          actions={
            <CopyButton
              text={{
                html: htmlEvidenceBySource(payload, payload.in_silico_predictions, null, []),
                text: tsvEvidenceBySource(payload, payload.in_silico_predictions, null, []),
              }}
              label="Copy in-silico (paste into Excel for formatted table)"
            />
          }
        >
          <LazySection<ComputationalDeepDiveSection>
            key={`insilico-${variantKey}${lazyOverrides.has('computational_deep_dive') ? '-lazy' : ''}`}
            eagerData={
              lazyOverrides.has('computational_deep_dive')
                ? null
                : payload.report_profile?.computational_deep_dive
            }
            sectionId="computational_deep_dive"
            request={effectiveSummaryRequest ?? null}
            unwrap={(env) => (env.payload as ComputationalDeepDiveSection | null) ?? null}
            forceLoad={lazyOverrides.has('computational_deep_dive')}
          >
            {(section) => (
              <>
                <CompositeVerdictBar predictors={section.predictors} />
                <CalibratedInSilicoTable predictors={section.predictors} />
              </>
            )}
          </LazySection>
          {/* Loss-of-function (PVS1) — NMD prediction + Abou-Tayoun PVS1 tree.
              Computational, so it lives with the in-silico predictions; N/A for
              non-null variants (e.g. missense). */}
          <LossOfFunctionBlock consequence={row0?.consequence ?? row0?.variation_type ?? null} />
          {/* EAMOS-computed ACMG/AMP advisory — the synthesis capstone of §2:
              draws the points decision (gauge + plane + waterfall) by combining
              the predictors above with population/LoF/functional evidence. The
              legacy Richards categorical estimate folds into an audit disclosure. */}
          <EamosAcmgClassifier
            data={payload.acmg_criteria_scaffold}
            computed={computedClassification}
            mock={computedIsMock}
          />
        </Card>

        {/* 3 · Population frequency (gnomAD) — AF thermometer + constraint
            readout above the world map / ancestry / age tabs. */}
        <div id="population_frequency" className="scroll-mt-24" />
        {populationSection && (
          <Card
            number={3}
            title="gnomAD population frequency"
            meta="genetic ancestry groups | source age distribution"
            actions={
              <CopyButton
                text={{
                  html: htmlPopulation(payload, payload.population_frequency_detail),
                  text: tsvPopulation(payload, payload.population_frequency_detail),
                }}
                label="Copy population frequency (paste into Excel for formatted table)"
              />
            }
          >
            <AfThermometer af={populationSection.overall?.total?.allele_frequency ?? null} evidence={data.evidence} />
            <PopulationFrequencySection section={populationSection} />
          </Card>
        )}

        {/* 4 · Gene & locus context — Slice B build 1 swaps the gene-snapshot
            SVG + expandable transcript figures for the new ReportGeneViewer
            (compressed exon track + queried variant lollipop + ClinVar
            variant density). Locus ±40 bp window + MolecularContextBlock
            (gnomAD constraint / ClinGen dosage / overlapping CNVs) stay.
            Source-backed protein-domain and optional AlphaMissense tracks now
            render inside ReportGeneViewer. */}
        <div id="gene_context" className="scroll-mt-24" />
        <Card
          number={4}
          title="Gene & locus context"
          meta={
            header?.gene && header?.transcript
              ? `${header.gene} · ${header.transcript}`
              : header?.gene || 'Gene context'
          }
          actions={
            <CopyButton
              text={{
                html: htmlGeneContextSnapshot(
                  payload,
                  payload.report_profile?.gene_context_snapshot ?? null,
                  payload.locus_context,
                ),
                text: tsvGeneContextSnapshot(
                  payload,
                  payload.report_profile?.gene_context_snapshot ?? null,
                  payload.locus_context,
                ),
              }}
              label="Copy gene context (paste into Excel for formatted table)"
            />
          }
        >
          {header?.gene && header?.cdna && (
            <ReportGeneViewer
              gene={header.gene}
              cdna={header.cdna}
              transcript={header.transcript ?? null}
              demo={demo}
            />
          )}

          <MolecularContextBlock evidence={data.evidence} />
        </Card>

        {/* 5 · Disease & curated variants — disease mechanism + curated
            variant distribution + associated conditions + the new
            GeneDiseaseBlock (ClinGen Gene-Disease Validity from the
            `gene_disease` evidence row). PublicationsCallout moved to §6.
            (Renamed from old §4 "Gene context & associated conditions".) */}
        <div id="associated_conditions" className="scroll-mt-24" />
        <div id="curated_variants" className="scroll-mt-24" />
        <Card
          number={5}
          title="Disease & curated variants"
          meta={geneContextMeta}
          actions={
            <CopyButton
              text={{
                html: htmlDiseaseAndConditions(
                  payload,
                  payload.curated_variants_distribution,
                  payload.associated_conditions,
                ),
                text: tsvDiseaseAndConditions(
                  payload,
                  payload.curated_variants_distribution,
                  payload.associated_conditions,
                ),
              }}
              label="Copy conditions (paste into Excel for formatted table)"
            />
          }
        >
          <DiseaseSection payload={payload} embedded sectionTarget={targetFor('disease_mechanism')} />
          <CuratedVariantsGrid data={payload.curated_variants_distribution} />
          <AssociatedConditions data={payload.associated_conditions} />
          <GeneDiseaseBlock evidence={data.evidence} />
        </Card>

        {/* 6 · Publication literature. */}
        {/* LazySection v1: when the backend ships `publications_literature`
            inline (today: offline fixture + eager live), we render the existing
            PubMedSection immediately via `eagerData`. When the eager payload
            is trimmed (M-007 / M11 follow-up), the IntersectionObserver path
            kicks in and lazy-fetches via /api/v1/lookup/sections.

            `?lazy=publications` forces eagerData=null AND forceLoad=true so
            the lazy fetch fires immediately today against Codex's already-
            shipped /lookup/sections endpoint — the M11/M-007 contract canary.
            Bypassing IntersectionObserver makes the hatch deterministic in
            headless preflight runs; IO timing is exercised separately via
            vitest. Key suffix forces a clean remount on toggle so
            LazyFetchSection state resets. */}
        <div id="publications" className="scroll-mt-24" />
        <LazySection<PublicationLiterature>
          key={`pubs-${variantKey}${lazyOverrides.has('publications') ? '-lazy' : ''}`}
          eagerData={lazyOverrides.has('publications') ? null : payload.publications_literature}
          sectionId="publications"
          request={effectiveSummaryRequest ?? null}
          unwrap={(env) => (env.payload as PublicationLiterature | null) ?? null}
          forceLoad={lazyOverrides.has('publications')}
        >
          {(lit) => (
            <PubMedSection
              payload={{ ...payload, publications_literature: lit }}
              number={6}
              actions={
                <CopyButton
                  text={{
                    html: htmlPublications(payload, lit),
                    text: tsvPublications(payload, lit),
                  }}
                  label="Copy publications (paste into Excel for formatted table)"
                />
              }
            />
          )}
        </LazySection>

        {/* 7 · Active trials & approved therapies. */}
        <div id="trials" className="scroll-mt-24" />
        <TrialsSection
          key={`trials-${variantKey}`}
          payload={payload}
          number={7}
          actions={
            <CopyButton
              text={{
                html: htmlTrials(
                  payload,
                  payload.report_profile?.therapies_trials?.trial_rows ?? [],
                ),
                text: tsvTrials(
                  payload,
                  payload.report_profile?.therapies_trials?.trial_rows ?? [],
                ),
              }}
              label="Copy trials (paste into Excel for formatted table)"
            />
          }
        />

        {/* The AI evidence summary (formerly §8) now lives in the Ask-Eamos
            work-rail (docs/ai-work-rail/spec.md) — on-demand, not buried at the
            foot of the read. */}

        {/* Optional plain-language decoder (not part of the numbered chain). */}
        <VariantDecoder decoder={payload.variant_decoder} />
      </div>
    </div>
  )
}


interface ErrorBlockProps {
  variant: 'generic' | 'offline' | 'unresolved'
  message?: string
  query: string
  onRetry: () => void
  backHref: string
  backLabel: string
  showDemo: boolean
}

function ErrorBlock({ variant, message, query, onRetry, backHref, backLabel, showDemo }: ErrorBlockProps) {
  const isOffline = variant === 'offline'
  const isUnresolved = variant === 'unresolved'
  const title = isOffline
    ? 'Backend offline'
    : isUnresolved
      ? 'Couldn’t resolve this variant'
      : 'Lookup failed'

  return (
    <section
      role="alert"
      style={{
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 14,
        padding: '24px 28px',
        color: 'var(--ink)',
      }}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="inline-flex shrink-0 items-center justify-center"
          style={{
            width: 28,
            height: 28,
            borderRadius: 999,
            background: 'var(--bg)',
            border: '0.5px solid var(--warn-bdr)',
            color: 'var(--warn)',
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <h2
            style={{
              fontFamily: 'var(--display)',
              fontWeight: 600,
              fontSize: 16,
              letterSpacing: '-0.01em',
              color: 'var(--ink)',
              margin: 0,
            }}
          >
            {title}
          </h2>
          {query && (
            <div
              className="mt-1"
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 12.5,
                color: 'var(--ink-3)',
              }}
            >
              {query}
            </div>
          )}
          {isOffline ? (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
              }}
            >
              The Eamos service is temporarily unavailable — this can happen if the
              server is waking from idle. Please wait a few moments and try again.
            </p>
          ) : isUnresolved ? (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
              }}
            >
              We reached the databases, but none could resolve this query to
              genomic coordinates: Ensembl and VariantValidator didn’t
              recognise the gene/HGVS pair. This isn’t a network failure.
              Double-check the transcript and cDNA (or try the rsID), then
              retry.
            </p>
          ) : (
            <p
              className="mt-2.5"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: 'var(--ink-2)',
                margin: '10px 0 0',
                wordBreak: 'break-word',
              }}
            >
              {message}
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {isOffline && (
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex items-center gap-1.5 transition-colors"
                style={{
                  padding: '7px 14px',
                  borderRadius: 10,
                  border: '0.5px solid var(--ink-2)',
                  background: 'var(--ink-2)',
                  color: '#fff',
                  fontSize: 12.5,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Try again
              </button>
            )}
            <Link
              href={backHref}
              style={{
                padding: '7px 14px',
                borderRadius: 10,
                border: '0.5px solid var(--line-2)',
                background: 'var(--bg)',
                color: 'var(--ink-2)',
                fontSize: 12.5,
                fontWeight: 600,
                textDecoration: 'none',
              }}
            >
              {backLabel}
            </Link>
            {showDemo && !isOffline && (
              <Link
                href="/report?gene=USH2A&cdna=c.2276G%3ET"
                style={{
                  fontSize: 12,
                  color: 'var(--ink-3)',
                  textDecoration: 'underline',
                  textUnderlineOffset: 3,
                  marginLeft: 4,
                }}
              >
                View the USH2A sample report instead
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

// Map a free-form ACMG classification string to the Card accent Verdict union.
// Mirrors VariantHeader's deriveClassificationLabel but returns the typed union
// (or null when the source string isn't a recognised tier).
function deriveClassificationVerdict(acmg: string | null | undefined): Verdict | null {
  if (!acmg) return null
  const raw = acmg.toLowerCase()
  if (raw.includes('unavailable') || raw.includes('not found')) return null
  if (raw.includes('likely pathogenic')) return 'Likely pathogenic'
  if (raw.includes('likely benign')) return 'Likely benign'
  if (raw.includes('pathogenic')) return 'Pathogenic'
  if (raw.includes('benign')) return 'Benign'
  if (raw.includes('vus') || raw.includes('uncertain')) return 'VUS'
  return null
}

// Input-format problem (client-detected, or server `input_unparseable:`).
// Deliberately NOT styled like ErrorBlock's amber failure panel — this is a
// neutral, user-actionable hint, and there is no retry (re-sending identical
// malformed input would fail identically).
function MalformedBlock({
  query,
  detail,
  backHref,
  backLabel,
  showDemo,
}: {
  query: string
  detail?: string
  backHref: string
  backLabel: string
  showDemo: boolean
}) {
  return (
    <section
      role="alert"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '24px 28px',
        color: 'var(--ink)',
      }}
    >
      <h2
        style={{
          fontFamily: 'var(--display)',
          fontWeight: 600,
          fontSize: 16,
          letterSpacing: '-0.01em',
          margin: 0,
        }}
      >
        Not a recognised variant
      </h2>
      {query && (
        <div
          className="mt-1"
          style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink-3)' }}
        >
          {query}
        </div>
      )}
      <p
        style={{
          fontSize: 13.5,
          lineHeight: 1.6,
          color: 'var(--ink-2)',
          margin: '10px 0 0',
        }}
      >
        {detail ??
          'Eamos couldn’t parse this as a variant. Try one of these formats:'}
      </p>
      <ul
        style={{
          margin: '10px 0 0',
          padding: 0,
          listStyle: 'none',
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        {[
          ['Gene + cDNA', 'USH2A c.2276G>T'],
          ['Transcript HGVS', 'NM_206933.4:c.2276G>T'],
          ['Genomic hg38', '1-216247118-C-A'],
          ['dbSNP', 'rs80338902'],
        ].map(([label, example]) => (
          <li
            key={label}
            style={{
              padding: '6px 10px',
              background: 'var(--bg-soft)',
              border: '0.5px solid var(--line)',
              borderRadius: 8,
              fontSize: 12,
              color: 'var(--ink-3)',
            }}
          >
            <span style={{ color: 'var(--ink-4)' }}>{label}: </span>
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>{example}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Link
          href={backHref}
          style={{
            padding: '7px 14px',
            borderRadius: 10,
            border: '0.5px solid var(--ink-2)',
            background: 'var(--ink-2)',
            color: '#fff',
            fontSize: 12.5,
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          {backLabel}
        </Link>
        {showDemo && (
          <Link
            href="/report?gene=USH2A&cdna=c.2276G%3ET"
            style={{
              fontSize: 12,
              color: 'var(--ink-3)',
              textDecoration: 'underline',
              textUnderlineOffset: 3,
              marginLeft: 4,
            }}
          >
            View the USH2A sample report instead
          </Link>
        )}
      </div>
    </section>
  )
}
