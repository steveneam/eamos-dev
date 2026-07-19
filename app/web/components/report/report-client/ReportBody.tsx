'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { AIStack } from '@/components/aistack/AIStack'
import { AcmgCriteriaFold } from '@/components/report/AcmgCriteriaFold'
import { AfThermometer } from '@/components/report/AfThermometer'
import { CalibratedInSilicoTable } from '@/components/report/CalibratedInSilicoTable'
import { CallCardsGrid } from '@/components/report/CallCardsGrid'
import { ClinVarBlock } from '@/components/report/ClinVarBlock'
import { CompositeVerdictBar } from '@/components/report/CompositeVerdictBar'
import { DataCurrencyLine } from '@/components/report/DataCurrencyLine'
import { DiseaseValidityDashboard } from '@/components/report/DiseaseValidityDashboard'
import { EamosAcmgClassifier } from '@/components/report/EamosAcmgClassifier'
import { ExpertPanelSection } from '@/components/report/ExpertPanelSection'
import { ExportMenu } from '@/components/report/ExportMenu'
import { GeneViewerErrorBoundary } from '@/components/report/GeneViewerErrorBoundary'
import { LazySection } from '@/components/report/LazySection'
import { LossOfFunctionBlock } from '@/components/report/LossOfFunctionBlock'
import { LovdBasicRecordsBlock } from '@/components/report/LovdBasicRecordsBlock'
import { MaveFunctionalBlock } from '@/components/report/MaveFunctionalBlock'
import { MolecularContextBlock } from '@/components/report/MolecularContextBlock'
import { PopulationFrequencySection } from '@/components/report/PopulationFrequencySection'
import { PubMedSection } from '@/components/report/PubMedSection'
import { ReportGeneViewer } from '@/components/report/ReportGeneViewer'
import { StickyVariantRibbon } from '@/components/report/StickyVariantRibbon'
import { TrialsSection } from '@/components/report/TrialsSection'
import { VariantDecoder } from '@/components/report/VariantDecoder'
import { VariantHeader } from '@/components/report/VariantHeader'
import { Card } from '@/components/ui/Card'
import { CopyButton } from '@/components/ui/CopyButton'
import type {
  ComputationalDeepDiveSection,
  ExpertPanelSection as ExpertPanelSectionData,
  LookupRequest,
  LookupResponse,
  LookupSectionId,
  ProteinDomainTrack,
  PublicationLiterature,
  TherapiesTrialsSection,
} from '@/lib/backend'
import {
  htmlDiseaseAndConditions,
  htmlEvidenceBySource,
  htmlGeneContextSnapshot,
  htmlPopulation,
  htmlPublications,
  htmlTrials,
} from '@/lib/report-html'
import { recordReportView, type VariantViewMetric } from '@/lib/report-views'
import {
  tsvDiseaseAndConditions,
  tsvEvidenceBySource,
  tsvGeneContextSnapshot,
  tsvPopulation,
  tsvPublications,
  tsvTrials,
} from '@/lib/report-tsv'

import {
  ExpertPanelPartialNote,
  ReportSectionEmptyCard,
  ReportSectionErrorCard,
  ReportSectionSkeletonCard,
  ReportSectionSlot,
  ReportSectionState,
  ReportSectionStateCard,
  stateFromEnvelope,
} from './ReportSectionPrimitives'
import {
  deriveClassificationVerdict,
  reportViewQueryId,
} from './reportClientModel'

export function ReportAiPanel({ data, queryFallback }: { data: LookupResponse; queryFallback: string }) {
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

export function ReportBody({ data, query, summaryRequest, lazyOverrides, demo = false }: ReportBodyProps) {
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
  const reportProteinDomainTrack =
    (payload.report_profile?.gene_context_snapshot?.protein_domain_track ??
      payload.report_profile?.molecular_context?.protein_domain_track ??
      null) as ProteinDomainTrack | null
  const transcriptHgvs = row0?.transcript_hgvs ?? null
  const ribbonTranscript = header?.transcript ?? transcriptHgvs?.split(':')[0] ?? undefined
  const ribbonHgvsC = header?.cdna ?? transcriptHgvs?.split(':')[1] ?? undefined
  const ribbonHgvsP = header?.protein_change ?? row0?.protein_change ?? undefined
  const [viewMetric, setViewMetric] = useState<VariantViewMetric | null>(null)
  const viewQueryId = useMemo(() => reportViewQueryId(data, query), [data, query])
  const activeViewMetric =
    viewMetric && viewQueryId && viewMetric.query_id === viewQueryId.toLowerCase() ? viewMetric : null

  useEffect(() => {
    let cancelled = false
    if (!viewQueryId || demo) return () => {
      cancelled = true
    }
    void recordReportView(viewQueryId).then((metric) => {
      if (!cancelled && metric) setViewMetric(metric)
    })
    return () => {
      cancelled = true
    }
  }, [viewQueryId, demo])

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
  const populationSection = payload.report_profile?.population_frequency ?? null
  const populationCallCard =
    payload.call_cards?.cards.find((card) => card.card_id === 'population_frequency') ?? null
  const populationSourceStatus =
    populationSection?.source_status ??
    populationCallCard?.source_status ??
    (populationTarget?.match_level === 'unavailable' ? 'missing' : null)
  const populationUnavailableReason =
    populationSection?.unavailable_reason ??
    payload.population_frequency_detail?.unavailable_reason ??
    populationTarget?.warnings?.find(Boolean) ??
    populationCallCard?.warnings?.find(Boolean) ??
    null
  const populationWarnings = Array.from(
    new Set([
      ...(populationSection?.warnings ?? []),
      ...(payload.population_frequency_detail?.warnings ?? []),
      ...(populationTarget?.warnings ?? []),
      ...(populationCallCard?.warnings ?? []),
    ]),
  )
  const populationSourceUnreliable = ['failed', 'error', 'fallback', 'degraded', 'missing'].includes(
    (populationSourceStatus ?? '').toLowerCase(),
  )
  const populationAf = populationSection?.overall?.total?.allele_frequency ?? null

  const computedClassification = payload.eamos_computed_classification ?? null

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
        viewMetric={activeViewMetric}
        exportSlot={<ExportMenu data={data} variant="header" />}
      />

      {/* Honest data-currency disclosure (Varsome/Franklin do this). Uses the
          backend per-asset freshness block when present, with real per-source
          fetched_at as the fallback. */}
      <DataCurrencyLine data={data} freshness={payload.report_data_currency ?? null} />

      <div className="report-reading-flow">
        {/* Call cards sit just under the header as the at-a-glance verdicts.
            They're scannable summary; the numbered evidence sections begin
            below. */}
        <CallCardsGrid payload={payload} populationAf={populationAf} />

        {/* 1 · Clinical evidence — ClinGen expert panel + ClinVar + ACMG.
            ClinGen leads (highest weight for classification), then ClinVar,
            then the ACMG criteria fold. Leads the report (v3): the clinical
            classification is what a curator reads first. Verdict accent shows
            as the header leading dot (Card verdict prop). */}
        <ReportSectionSlot sectionId="clinical_evidence">
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
            placeholder={<ReportSectionState sectionId="clinical_evidence" state="loading" />}
            emptyView={<ExpertPanelPartialNote />}
            sectionStateView={(env, retryAction) => (
              <ReportSectionState
                sectionId="clinical_evidence"
                state={stateFromEnvelope(env)}
                detail={
                  env.warnings.length > 0
                    ? env.warnings.join(' | ')
                    : 'ClinGen/VCEP evidence is not fully source-backed for this lookup.'
                }
                action={retryAction}
              />
            )}
            errorView={() => <ExpertPanelPartialNote />}
          >
            {(section) => <ExpertPanelSection data={section} />}
          </LazySection>
          <ClinVarBlock evidence={data.evidence} />
          {/* LOVD is neutral presence context only. It is deliberately outside
              every classification and call-card computation path. */}
          <LovdBasicRecordsBlock section={payload.report_profile?.lovd_basic_records ?? null} />
          {/* Exact MaveDB raw measurements are neutral source context only.
              They cannot activate PS3/BS3, points, or a call-card theme. */}
          <MaveFunctionalBlock
            gene={row0?.gene}
            query={query}
            studies={
              payload.functional_evidence?.studies.filter(
                (study) => study.source_tags.includes('mavedb'),
              ) ?? []
            }
          />
          <AcmgCriteriaFold data={payload.acmg_criteria_scaffold} />
        </Card>
        </ReportSectionSlot>

        {/* 2 · In-silico predictions — engines + calibrated buckets only.
            Verdict accent and ClinVar/ACMG live in §1 Clinical evidence;
            per-source data for variant_validator/gnomad/ensembl/spliceai/
            clingen/gene_disease/molecular_context/computational_annotations/
            pubmed/litvar2/clinical_trials/vep is rendered elsewhere or in the
            variant header. */}
        <ReportSectionSlot sectionId="evidence_by_source">
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
            placeholder={<ReportSectionState sectionId="evidence_by_source" state="loading" />}
            emptyView={<ReportSectionState sectionId="evidence_by_source" state="empty" />}
            sectionStateView={(env, retryAction) => (
              <ReportSectionState
                sectionId="evidence_by_source"
                state={stateFromEnvelope(env)}
                detail={env.warnings.join(' | ') || undefined}
                action={retryAction}
              />
            )}
            errorView={(message, retryAction) => (
              <ReportSectionState
                sectionId="evidence_by_source"
                state="failed"
                detail={message}
                action={retryAction}
              />
            )}
          >
            {(section) => (
              <>
                <CompositeVerdictBar selectionAccounting={section.selection_accounting} />
                <CalibratedInSilicoTable predictors={section.predictors} warnings={section.warnings} />
              </>
            )}
          </LazySection>
          {/* Loss-of-function (PVS1) — NMD prediction + Abou-Tayoun PVS1 tree.
              Computational, so it lives with the in-silico predictions; N/A for
              non-null variants (e.g. missense). */}
          <LossOfFunctionBlock
            consequence={row0?.consequence ?? row0?.variation_type ?? null}
            computed={computedClassification}
          />
          {/* EAMOS-computed ACMG/AMP advisory — the synthesis capstone of §2:
              draws the points decision (gauge + plane + waterfall) by combining
              the predictors above with population/LoF/functional evidence. The
              legacy Richards categorical estimate folds into an audit disclosure. */}
          <EamosAcmgClassifier
            data={payload.acmg_criteria_scaffold}
            computed={computedClassification}
          />
        </Card>
        </ReportSectionSlot>

        {/* 3 · Population frequency (gnomAD) — AF thermometer + constraint
            readout above the world map / ancestry / age tabs. */}
        <ReportSectionSlot sectionId="population_frequency">
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
            {populationSection && !populationSourceUnreliable && (
              <AfThermometer
                af={populationSection.overall?.total?.allele_frequency ?? null}
                evidence={data.evidence}
                computed={computedClassification}
              />
            )}
            <PopulationFrequencySection
              section={populationSection}
              unavailable={{
                sourceStatus: populationSourceStatus,
                unavailableReason: populationUnavailableReason,
                warnings: populationWarnings,
                variantId: payload.population_frequency_detail?.variant_id ?? null,
                dataset: payload.population_frequency_detail?.dataset ?? null,
                genomeBuild: populationSection?.genome_build ?? null,
                sequencingType: payload.population_frequency_detail?.sequencing_type ?? null,
              }}
            />
          </Card>
        </ReportSectionSlot>

        {/* 4 · Gene & locus context — Slice B build 1 swaps the gene-snapshot
            SVG + expandable transcript figures for the new ReportGeneViewer
            (compressed exon track + queried variant lollipop + ClinVar
            variant density). Locus ±40 bp window + MolecularContextBlock
            (gnomAD constraint / ClinGen dosage / overlapping CNVs) stay.
            Source-backed protein-domain and optional AlphaMissense tracks now
            render inside ReportGeneViewer. */}
        <ReportSectionSlot sectionId="gene_context">
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
            <GeneViewerErrorBoundary gene={header.gene} cdna={header.cdna}>
              <ReportGeneViewer
                gene={header.gene}
                cdna={header.cdna}
                transcript={header.transcript ?? null}
                geneContextSnapshot={payload.report_profile?.gene_context_snapshot ?? null}
                proteinDomainTrack={reportProteinDomainTrack}
                markerClassification={
                  payload.report_profile?.header?.classification ??
                  payload.report_profile?.acmg_worksheet?.classification ??
                  payload.acmg_classification ??
                  null
                }
                demo={demo}
              />
            </GeneViewerErrorBoundary>
          )}

          <MolecularContextBlock evidence={data.evidence} />
        </Card>
        </ReportSectionSlot>

        {/* 5 · Disease & curated variants. DiseaseValidityDashboard owns the
            condition navigator, gene-disease validity, and curated distribution. */}
        <ReportSectionSlot sectionId="associated_conditions">
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
          <DiseaseValidityDashboard
            payload={payload}
            evidence={data.evidence}
            sectionTarget={targetFor('disease_mechanism')}
          />
        </Card>
        </ReportSectionSlot>

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
        <ReportSectionSlot sectionId="publications">
        <LazySection<PublicationLiterature>
          key={`pubs-${variantKey}${lazyOverrides.has('publications') ? '-lazy' : ''}`}
          eagerData={lazyOverrides.has('publications') ? null : payload.publications_literature}
          sectionId="publications"
          request={effectiveSummaryRequest ?? null}
          unwrap={(env) => (env.payload as PublicationLiterature | null) ?? null}
          forceLoad={lazyOverrides.has('publications')}
          placeholder={<ReportSectionSkeletonCard sectionId="publications" />}
          emptyView={<ReportSectionEmptyCard sectionId="publications" />}
          sectionStateView={(env, retryAction) => (
            <ReportSectionStateCard
              sectionId="publications"
              state={stateFromEnvelope(env)}
              detail={env.warnings.join(' | ') || undefined}
              action={retryAction}
            />
          )}
          errorView={(message, retryAction) => (
            <ReportSectionErrorCard sectionId="publications" message={message} action={retryAction} />
          )}
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
        </ReportSectionSlot>

        {/* 7 · Active trials & approved therapies. */}
        <ReportSectionSlot sectionId="trials">
        <LazySection<TherapiesTrialsSection>
          key={`trials-${variantKey}${lazyOverrides.has('therapies_trials') ? '-lazy' : ''}`}
          eagerData={
            lazyOverrides.has('therapies_trials')
              ? null
              : payload.report_profile?.therapies_trials
          }
          sectionId="therapies_trials"
          request={effectiveSummaryRequest ?? null}
          unwrap={(env) => (env.payload as TherapiesTrialsSection | null) ?? null}
          forceLoad={lazyOverrides.has('therapies_trials')}
          placeholder={<ReportSectionSkeletonCard sectionId="trials" />}
          emptyView={<ReportSectionEmptyCard sectionId="trials" />}
          sectionStateView={(env, retryAction) => (
            <ReportSectionStateCard
              sectionId="trials"
              state={stateFromEnvelope(env)}
              detail={env.warnings.join(' | ') || undefined}
              action={retryAction}
            />
          )}
          errorView={(message, retryAction) => (
            <ReportSectionErrorCard sectionId="trials" message={message} action={retryAction} />
          )}
        >
          {(section) => (
            <TrialsSection
              payload={payload}
              section={section}
              number={7}
              actions={
                <CopyButton
                  text={{
                    html: htmlTrials(payload, section.trial_rows ?? []),
                    text: tsvTrials(payload, section.trial_rows ?? []),
                  }}
                  label="Copy trials (paste into Excel for formatted table)"
                />
              }
            />
          )}
        </LazySection>
        </ReportSectionSlot>

        {/* The AI evidence summary (formerly §8) now lives in the Ask-Eamos
            work-rail (docs/ai-work-rail/spec.md) — on-demand, not buried at the
            foot of the read. */}

        {/* Optional plain-language decoder (not part of the numbered chain). */}
        <VariantDecoder decoder={payload.variant_decoder} />
      </div>
    </div>
  )
}
