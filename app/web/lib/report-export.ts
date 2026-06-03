/**
 * Whole-report export — composes the per-section serializers (report-tsv.ts /
 * report-html.ts) into a single document for the "Copy full report" + "Download"
 * export actions. No new serialization: each section reuses the exact builder its
 * section-level Copy button already uses, so the full-report export and the
 * per-section copies stay byte-identical.
 */
import type { LookupResponse, ReportPayload, VariantReportHeader } from './backend'
import {
  tsvAISummary,
  tsvDiseaseAndConditions,
  tsvEvidenceBySource,
  tsvGeneContextSnapshot,
  tsvPopulation,
  tsvPublications,
  tsvTrials,
} from './report-tsv'
import {
  htmlAISummary,
  htmlDiseaseAndConditions,
  htmlEvidenceBySource,
  htmlGeneContextSnapshot,
  htmlPopulation,
  htmlPublications,
  htmlTrials,
} from './report-html'

export interface FullReportExport {
  /** Plain-text / TSV document — clipboard `text/plain` + the download file body. */
  text: string
  /** Rich HTML document — clipboard `text/html` (Word / Sheets paste with tables). */
  html: string
  /** Filename stem for downloads, e.g. "eamos-report-USH2A-c2276G-T". */
  filenameBase: string
}

const DISCLAIMER =
  'Decision-support only. EAMOS aggregates public sources; a qualified clinician confirms every classification. Every datum is source-linked in the live report.'

function variantLine(payload: ReportPayload): string {
  const h: VariantReportHeader | null | undefined = payload.report_profile?.header
  if (h) return [h.gene, h.cdna, h.protein_change, h.genomic_hg38].filter(Boolean).join(' · ')
  const r = payload.variant_summary_rows[0]
  if (r) return [r.gene, r.transcript_hgvs, r.protein_change].filter(Boolean).join(' · ')
  return 'Variant report'
}

function clinvarEvidenceRows(data: LookupResponse) {
  return data.evidence
    .filter((e) => e.source?.toLowerCase() === 'clinvar')
    .map((e) => ({ source: e.source, status: e.status, summary: e.summary }))
}

function filenameBase(payload: ReportPayload): string {
  const h = payload.report_profile?.header
  const r = payload.variant_summary_rows[0]
  const gene = h?.gene ?? r?.gene ?? 'variant'
  const change = h?.cdna ?? r?.protein_change ?? ''
  const stem = `eamos-report-${gene}-${change}`
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  return stem || 'eamos-report'
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export function buildFullReportExport(data: LookupResponse): FullReportExport {
  const payload = data.report_payload
  const rows = clinvarEvidenceRows(data)
  const generatedAt = new Date().toISOString()
  const vline = variantLine(payload)

  const text = [
    [
      'EAMOS Variant Evidence Report',
      `Variant\t${vline}`,
      `Generated\t${generatedAt}`,
      `Disclaimer\t${DISCLAIMER}`,
    ].join('\n'),
    tsvPopulation(payload, payload.population_frequency_detail),
    tsvEvidenceBySource(payload, payload.in_silico_predictions, null, []),
    tsvEvidenceBySource(payload, null, payload.acmg_criteria_scaffold, rows),
    tsvGeneContextSnapshot(
      payload,
      payload.report_profile?.gene_context_snapshot ?? null,
      payload.locus_context,
    ),
    tsvDiseaseAndConditions(
      payload,
      payload.curated_variants_distribution,
      payload.associated_conditions,
    ),
    tsvPublications(payload, payload.publications_literature),
    tsvTrials(payload, payload.report_profile?.therapies_trials?.trial_rows ?? []),
    tsvAISummary(payload),
  ].join('\n\n')

  const html = [
    '<h1>EAMOS Variant Evidence Report</h1>',
    `<p><strong>Variant:</strong> ${escapeHtml(vline)}<br/>` +
      `<strong>Generated:</strong> ${escapeHtml(generatedAt)}<br/>` +
      `<em>${escapeHtml(DISCLAIMER)}</em></p>`,
    htmlPopulation(payload, payload.population_frequency_detail),
    htmlEvidenceBySource(payload, payload.in_silico_predictions, null, []),
    htmlEvidenceBySource(payload, null, payload.acmg_criteria_scaffold, rows),
    htmlGeneContextSnapshot(
      payload,
      payload.report_profile?.gene_context_snapshot ?? null,
      payload.locus_context,
    ),
    htmlDiseaseAndConditions(
      payload,
      payload.curated_variants_distribution,
      payload.associated_conditions,
    ),
    htmlPublications(payload, payload.publications_literature),
    htmlTrials(payload, payload.report_profile?.therapies_trials?.trial_rows ?? []),
    htmlAISummary(payload),
  ].join('\n')

  return { text, html: `<div>${html}</div>`, filenameBase: filenameBase(payload) }
}
