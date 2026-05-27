'use client'
import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { TopNav } from '@/components/layout/TopNav'
import { ModePill } from '@/components/layout/ModePill'
import { EamosSearch } from '@/components/landing/EamosSearch'
import { VariantHeader } from '@/components/report/VariantHeader'
import { VariantDecoder } from '@/components/report/VariantDecoder'
import { AIStack } from '@/components/aistack/AIStack'
import { EvidenceTable } from '@/components/report/EvidenceTable'
import { DiseaseSection } from '@/components/report/DiseaseSection'
import { TrialsSection } from '@/components/report/TrialsSection'
import { PubMedSection } from '@/components/report/PubMedSection'
import { LocusContext } from '@/components/report/LocusContext'
import { InSilicoGrid } from '@/components/report/InSilicoGrid'
import { AcmgCriteriaFold } from '@/components/report/AcmgCriteriaFold'
import { CuratedVariantsGrid } from '@/components/report/CuratedVariantsGrid'
import { AssociatedConditions } from '@/components/report/AssociatedConditions'
import { PublicationsCallout } from '@/components/report/PublicationsCallout'
import { PopulationFrequencySection } from '@/components/report/PopulationFrequencySection'
import { CallCardsGrid } from '@/components/report/CallCardsGrid'
import { SearchInterpretationPanel } from '@/components/report/SearchInterpretationPanel'
import { GeneContextSnapshotSection } from '@/components/report/GeneContextSnapshotSection'
import { StickyVariantRibbon } from '@/components/report/StickyVariantRibbon'
import { MatrixOverture } from '@/components/report/MatrixOverture'
import { Card, type Verdict } from '@/components/ui/Card'
import { CopyButton } from '@/components/ui/CopyButton'
import { variantLookup } from '@/lib/api'
import { cleanQuery, isLikelyUnparseable } from '@/lib/variant-format'
import { reportHrefForQuery } from '@/lib/variant-search'
import { RPE65_SAMPLE } from '@/lib/sample-report'
import {
  tsvAISummary,
  tsvDiseaseAndConditions,
  tsvEvidenceBySource,
  tsvGeneContextSnapshot,
  tsvPopulation,
  tsvPublications,
  tsvTrials,
} from '@/lib/report-tsv'
import {
  htmlAISummary,
  htmlDiseaseAndConditions,
  htmlEvidenceBySource,
  htmlGeneContextSnapshot,
  htmlPopulation,
  htmlPublications,
  htmlTrials,
} from '@/lib/report-html'
import { SOURCES } from '@/lib/sources'
import type {
  LookupRequest,
  LookupResponse,
  SearchInputCandidate,
  SearchInputInterpretation,
} from '@/lib/backend'

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; data: LookupResponse }
  | { kind: 'malformed'; query: string; detail?: string }
  | { kind: 'unresolved'; query: string }
  | { kind: 'interpretation'; query: string; interpretation: SearchInputInterpretation; detail?: string | null }
  | { kind: 'error'; message: string }
  | { kind: 'offline' }

export function ReportClient() {
  const params = useSearchParams()
  const router = useRouter()
  const gene = params.get('gene')?.trim() ?? ''
  const cdna = params.get('cdna')?.trim() ?? ''
  const transcript = params.get('transcript')?.trim() ?? ''
  const proteinChange = params.get('protein_change')?.trim() ?? ''
  const q = params.get('q')?.trim() ?? ''
  const demo = params.get('demo') !== null

  const [state, setState] = useState<LoadState>({ kind: 'idle' })
  const [attempt, setAttempt] = useState(0)
  // Focus-expand: the compact search grows from a narrower resting width to fill
  // the bar when focused — on desktop AND mobile. Percentage width gives a smooth
  // %→% transition (no px overshoot/snap) at any viewport.
  const [searchFocused, setSearchFocused] = useState(false)

  // M7 live-wire: mirror the LookupRequest the report itself uses so the
  // MatrixOverture can call lookupSummary() and upgrade its mock tiles.
  // Demo / sample mode leaves request undefined → overture stays mock-only.
  const summaryRequest = useMemo<LookupRequest | undefined>(() => {
    if (demo) return undefined
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
  }, [demo, gene, cdna, transcript, proteinChange, q])

  useEffect(() => {
    let cancelled = false

    if (demo || (!gene && !cdna && !q)) {
      setState({ kind: 'ready', data: RPE65_SAMPLE })
      return
    }

    if (!gene && !cdna && q) {
      // Raw searches resolve through the backend parser/candidate gate before
      // any report payload is rendered.
      setState({ kind: 'loading' })
      variantLookup({ search_text: q, species: 'human' })
        .then((data) => {
          if (cancelled) return
          const interpretation = data.search_interpretation ?? null
          const responseGene =
            data.report_payload.report_profile?.header?.gene ??
            data.report_payload.variant_summary_rows[0]?.gene
          if (interpretation && !responseGene) {
            setState({
              kind: 'interpretation',
              query: q,
              interpretation,
              detail: data.report_payload.limitations,
            })
            return
          }
          if (responseGene && interpretation?.gene && responseGene.toUpperCase() !== interpretation.gene.toUpperCase()) {
            setState({
              kind: 'error',
              message: `Lookup returned data for ${responseGene}, but the search resolved to ${interpretation.gene}. The report was not rendered to avoid showing stale variant facts.`,
            })
            return
          }
          setState({ kind: 'ready', data })
        })
        .catch((err: Error) => {
          if (cancelled) return
          if (err instanceof TypeError) {
            setState({ kind: 'offline' })
          } else {
            setState({ kind: 'error', message: err.message })
          }
        })
      return () => {
        cancelled = true
      }
    }

    if (!gene || !cdna) {
      setState({
        kind: 'error',
        message: 'Both a gene and a cDNA (or HGVS) change are required.',
      })
      return
    }

    // BE-8 mirror: clean before building the request (never lowercases HGVS).
    const cleanedCdna = cleanQuery(cdna)
    const probe = `${gene.toUpperCase()} ${cleanedCdna}`.trim()

    // Client-side malformed guard — only short-circuit on input that's
    // unparseable every way (a lone rs…/p.…/coord is valid backend input and
    // must NOT be blocked here). The backend is authoritative and emits
    // `input_unparseable:<kind>` for the cases this guard lets through.
    if (isLikelyUnparseable(gene, cdna)) {
      setState({ kind: 'malformed', query: probe })
      return
    }

    setState({ kind: 'loading' })
    variantLookup({
      gene,
      cdna: cleanedCdna,
      transcript: transcript || null,
      protein_change: proteinChange || null,
      species: 'human',
    })
      .then((data) => {
        if (cancelled) return
        // BE-12 frozen warning codes — see plans/v2-backend.md.
        const warnings = data.warnings ?? []
        if (warnings.some((c) => c.startsWith('input_unparseable:'))) {
          setState({
            kind: 'malformed',
            query: probe,
            detail: data.report_payload.limitations ?? undefined,
          })
          return
        }
        if (warnings.includes('no_genomic_resolution')) {
          setState({ kind: 'unresolved', query: probe })
          return
        }
        const responseGene =
          data.report_payload.report_profile?.header?.gene ??
          data.report_payload.variant_summary_rows[0]?.gene
        if (responseGene && responseGene.toUpperCase() !== gene.toUpperCase()) {
          setState({
            kind: 'error',
            message: `Lookup returned data for ${responseGene}, but the URL requested ${gene}. The report was not rendered to avoid showing stale variant facts.`,
          })
          return
        }
        setState({ kind: 'ready', data })
      })
      .catch((err: Error) => {
        if (cancelled) return
        // fetch() throws TypeError for connection-refused / DNS / CORS — i.e.
        // the dev backend isn't running. 4xx/5xx responses come through
        // parseResponse as a plain Error and route to the generic branch.
        // (variantLookup already retried once with backoff for network/5xx.)
        if (err instanceof TypeError) {
          setState({ kind: 'offline' })
        } else {
          setState({ kind: 'error', message: err.message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [gene, cdna, transcript, proteinChange, q, demo, attempt])

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
            width: searchFocused ? '100%' : '78%',
            transition: 'width 460ms var(--ease-emphasized)',
          }}
        >
          <EamosSearch size="compact" tone="light" onSubmit={handleSearch} />
        </div>
      </TopNav>

      <main className="mx-auto" style={{ maxWidth: 'var(--maxw-report-frame)', padding: '32px 32px 80px' }}>
        {state.kind === 'loading' && <LoadingBlock query={queryLabel} />}
        {state.kind === 'error' && (
          <ErrorBlock
            variant="generic"
            message={state.message}
            query={queryLabel}
            canRetry={Boolean((gene && cdna) || q)}
            onRetry={() => setAttempt((n) => n + 1)}
          />
        )}
        {state.kind === 'offline' && (
          <ErrorBlock
            variant="offline"
            query={queryLabel}
            canRetry={Boolean((gene && cdna) || q)}
            onRetry={() => setAttempt((n) => n + 1)}
          />
        )}
        {state.kind === 'malformed' && (
          <MalformedBlock query={state.query} detail={state.detail} />
        )}
        {state.kind === 'unresolved' && (
          <ErrorBlock
            variant="unresolved"
            query={state.query}
            canRetry
            onRetry={() => setAttempt((n) => n + 1)}
          />
        )}
        {state.kind === 'interpretation' && (
          <SearchInterpretationPanel
            query={state.query}
            interpretation={state.interpretation}
            limitations={state.detail}
            onSelectCandidate={handleSelectCandidate}
          />
        )}
        {state.kind === 'ready' && (
          <ReportBody
            data={state.data}
            query={`${gene} ${cdna}`.trim() || state.data.query}
            summaryRequest={summaryRequest}
          />
        )}
      </main>
    </div>
  )
}

interface ReportBodyProps {
  data: LookupResponse
  query: string
  summaryRequest?: LookupRequest
}

function ReportBody({ data, query, summaryRequest }: ReportBodyProps) {
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

  // Ribbon handlers — mirror VariantHeader buttons (Copy/Share/Export) + open
  // CiteChip globally via ?cite=1.
  const handleCopy = () => {
    const label = [ribbonGene, ribbonTranscript && ribbonHgvsC ? `${ribbonTranscript}:${ribbonHgvsC}` : ribbonHgvsC, ribbonHgvsP ? `(${ribbonHgvsP})` : '']
      .filter(Boolean)
      .join(' ')
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(label)
    }
  }
  const handleShare = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(window.location.href)
    }
  }
  const handleExport = () => {
    if (typeof window !== 'undefined') window.print()
  }
  const handleCite = () => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('cite', '1')
    router.replace(`?${params.toString()}`, { scroll: false })
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
        onCopy={handleCopy}
        onShare={handleShare}
        onExport={handleExport}
        onCite={handleCite}
      />
      <VariantHeader payload={payload} query={query} />

      {/* M7 lookahead — 10-12 tiles that deep-link to each numbered section
          below. Live-wired to lookupSummary(); falls back to tiles synthesized
          from the existing ReportPayload when the backend is unreachable
          (TypeError) or when no request shape is available (demo mode). */}
      <MatrixOverture payload={payload} request={summaryRequest} />

      <div className="flex flex-col gap-3.5">
        {/* Call cards sit just under the header as the at-a-glance verdicts.
            They're scannable summary; the numbered evidence sections begin
            below. */}
        <CallCardsGrid payload={payload} />

        {/* 1 · Population frequency (gnomAD) */}
        {populationSection && (
          <Card
            number={1}
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
            <PopulationFrequencySection section={populationSection} />
          </Card>
        )}

        {/* 2 · Evidence by source (in-silico + per-source detail + ACMG) */}
        <div id="evidence_by_source" className="scroll-mt-24" />
        <Card
          number={2}
          title="Evidence by source"
          meta="in-silico · per-source detail · ACMG"
          verdict={verdict}
          actions={
            <CopyButton
              text={{
                html: htmlEvidenceBySource(
                  payload,
                  payload.in_silico_predictions,
                  payload.acmg_criteria_scaffold,
                  data.evidence.map((e) => ({ source: e.source, status: e.status, summary: e.summary })),
                ),
                text: tsvEvidenceBySource(
                  payload,
                  payload.in_silico_predictions,
                  payload.acmg_criteria_scaffold,
                  data.evidence.map((e) => ({ source: e.source, status: e.status, summary: e.summary })),
                ),
              }}
              label="Copy evidence (paste into Excel for formatted table)"
            />
          }
        >
          <InSilicoGrid data={payload.in_silico_predictions} />
          <EvidenceTable evidence={data.evidence} embedded />
          <AcmgCriteriaFold data={payload.acmg_criteria_scaffold} />
        </Card>

        {/* 3 · Gene context snapshot (Locus context merged in). */}
        <GeneContextSnapshotSection
          number={3}
          snapshot={payload.report_profile?.gene_context_snapshot}
          sectionTarget={targetFor('gene_context_snapshot')}
          locus={payload.locus_context}
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
        />

        {/* 4 · Gene context & associated conditions. */}
        <div id="associated_conditions" className="scroll-mt-24" />
        <div id="curated_variants" className="scroll-mt-24" />
        <Card
          number={4}
          title="Gene context & associated conditions"
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
          {!payload.publications_literature && (
            <PublicationsCallout data={payload.publications_callout} />
          )}
        </Card>

        {/* 5 · Publication literature. */}
        <div id="publications" className="scroll-mt-24" />
        <PubMedSection
          key={`pubs-${variantKey}`}
          payload={payload}
          number={5}
          actions={
            <CopyButton
              text={{
                html: htmlPublications(payload, payload.publications_literature),
                text: tsvPublications(payload, payload.publications_literature),
              }}
              label="Copy publications (paste into Excel for formatted table)"
            />
          }
        />

        {/* 6 · Active trials & approved therapies. */}
        <div id="trials" className="scroll-mt-24" />
        <TrialsSection
          key={`trials-${variantKey}`}
          payload={payload}
          number={6}
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

        {/* 7 · AI evidence summary — last so the deterministic source rows
            anchor the read before the synthesised summary. */}
        <div id="ai_summary" className="scroll-mt-24" />
        <Card
          number={7}
          title="AI evidence summary"
          meta="deterministic · cited"
          actions={
            <CopyButton
              text={{
                html: htmlAISummary(payload),
                text: tsvAISummary(payload),
              }}
              label="Copy AI summary (paste into Excel for formatted table)"
            />
          }
        >
          <AIStack payload={payload} runId={null} contextLabel={contextLabel} />
        </Card>

        {/* Optional plain-language decoder (not part of the numbered chain). */}
        <VariantDecoder decoder={payload.variant_decoder} />
      </div>
    </div>
  )
}

function LoadingBlock({ query }: { query: string }) {
  return (
    <section
      aria-busy="true"
      aria-live="polite"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '28px 32px',
      }}
    >
      <header className="flex items-center gap-3">
        <span
          aria-hidden
          style={{
            width: 18,
            height: 18,
            border: '2px solid var(--line)',
            borderTopColor: 'var(--teal)',
            borderRadius: '50%',
            animation: 'eamos-spin 0.9s linear infinite',
          }}
        />
        <div>
          <div
            className="uppercase"
            style={{
              fontSize: 10.5,
              fontWeight: 600,
              letterSpacing: '0.1em',
              color: 'var(--ink-4)',
            }}
          >
            Looking up variant
          </div>
          <div
            style={{
              fontFamily: 'var(--mono)',
              fontSize: 14,
              color: 'var(--ink)',
              marginTop: 2,
            }}
          >
            {query || '—'}
          </div>
        </div>
      </header>

      <ul
        className="mt-5 grid gap-2"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', listStyle: 'none', padding: 0, margin: 0 }}
      >
        {SOURCES.map((src, i) => (
          <li
            key={src.key}
            className="flex items-center gap-2"
            style={{
              padding: '8px 12px',
              background: 'var(--bg-soft)',
              border: '0.5px solid var(--line)',
              borderRadius: 10,
              fontSize: 12.5,
              color: 'var(--ink-3)',
            }}
          >
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: 999,
                background: 'var(--teal)',
                animation: `eamos-pulse 1.6s ease-in-out ${i * 0.18}s infinite`,
              }}
            />
            {src.label}
          </li>
        ))}
      </ul>

      <p
        className="mt-5"
        style={{ fontSize: 12, color: 'var(--ink-4)', margin: '20px 0 0' }}
      >
        Aggregating evidence across multiple databases — this can take up to ~15 seconds.
      </p>

      <style>{`
        @keyframes eamos-spin { to { transform: rotate(360deg); } }
        @keyframes eamos-pulse {
          0%, 100% { opacity: 0.35; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.25); }
        }
      `}</style>
    </section>
  )
}

interface ErrorBlockProps {
  variant: 'generic' | 'offline' | 'unresolved'
  message?: string
  query: string
  canRetry: boolean
  onRetry: () => void
}

function ErrorBlock({ variant, message, query, canRetry, onRetry }: ErrorBlockProps) {
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
            {canRetry && (
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
              href="/"
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
              Back to search
            </Link>
            {!isOffline && (
              <Link
                href="/report?demo=1"
                style={{
                  fontSize: 12,
                  color: 'var(--ink-3)',
                  textDecoration: 'underline',
                  textUnderlineOffset: 3,
                  marginLeft: 4,
                }}
              >
                View the RPE65 sample report instead
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
function MalformedBlock({ query, detail }: { query: string; detail?: string }) {
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
          ['Gene + cDNA', 'RPE65 c.260A>G'],
          ['Transcript HGVS', 'NM_000329.3:c.260A>G'],
          ['Protein', 'RPE65 p.Asp87Gly'],
          ['dbSNP', 'rs61752871'],
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
          href="/"
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
          Back to search
        </Link>
        <Link
          href="/report?demo=1"
          style={{
            fontSize: 12,
            color: 'var(--ink-3)',
            textDecoration: 'underline',
            textUnderlineOffset: 3,
            marginLeft: 4,
          }}
        >
          View the RPE65 sample report instead
        </Link>
      </div>
    </section>
  )
}
