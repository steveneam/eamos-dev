/**
 * Rich-HTML serializers for the variant report sections.
 *
 * Each builder returns a full `<table>` document fragment that Excel will
 * parse into a styled grid on paste: bold section banner that spans the
 * width, italicised variant line, sub-section bands where the section has
 * more than one logical block, bordered header rows with a tinted fill,
 * zebra-striped body rows, top-aligned wrap-text cells, sized columns for
 * the prose-heavy ones, and live hyperlinks where the source provides them.
 *
 * Pair with `lib/report-tsv.ts` — the rich HTML goes onto the clipboard as
 * `text/html` and the TSV goes on as `text/plain` so non-spreadsheet targets
 * (Notion, plain editors, AI chat) still get a sensible paste.
 *
 * Excel-friendly notes:
 *   - inline styles only (Excel ignores classes / external CSS)
 *   - `border-collapse: collapse` + per-cell `border` is the only border
 *     style Excel honours reliably
 *   - column widths come from `<col style="width: …px">`
 *   - `white-space: normal` + `word-wrap: break-word` enables wrap-text
 *   - `vertical-align: top` so multi-line cells anchor cleanly
 */

import type {
  AcmgCriteriaScaffold,
  AssociatedCondition,
  CuratedVariantsDistribution,
  GeneContextSnapshot,
  InSilicoPredictions,
  LocusContext,
  PopulationFrequencyDetail,
  PublicationLiterature,
  ReportPayload,
  TrialMatch,
  VariantReportHeader,
} from './backend'
import { productExportFacts } from './source-fact-policy'

/* ── Style tokens (Excel-safe sRGB) ─────────────────────────────────────── */

const C = {
  banner_bg: '#0E4F3A',
  banner_fg: '#FFFFFF',
  variant_bg: '#F4F6F8',
  variant_fg: '#4A5560',
  sub_bg: '#E6F2EC',
  sub_fg: '#0E4F3A',
  thead_bg: '#EEF3F6',
  thead_fg: '#1F2937',
  row_a: '#FFFFFF',
  row_b: '#FAFBFC',
  body_fg: '#1F2937',
  border: '#D6DBE0',
  border_strong: '#B9C2CB',
  link: '#0E4F3A',
} as const

const FONT_STACK = "Calibri, 'Segoe UI', Arial, sans-serif"

/* ── Helpers ────────────────────────────────────────────────────────────── */

function esc(value: unknown): string {
  if (value == null) return ''
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function joinPipes(values: (string | null | undefined)[]): string {
  return values.filter((v) => v != null && v !== '').join(' | ')
}

export function safeExportHref(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
      ? parsed.href
      : null
  } catch {
    return null
  }
}

function formatVariantLine(
  h: VariantReportHeader | null | undefined,
  payload: ReportPayload,
): string {
  if (h) {
    return [h.gene, h.cdna, h.protein_change, h.genomic_hg38].filter(Boolean).join(' · ')
  }
  const r0 = payload.variant_summary_rows[0]
  if (r0) return [r0.gene, r0.transcript_hgvs, r0.protein_change].filter(Boolean).join(' · ')
  return ''
}

/** Section banner + variant line as 2 colspan rows at the top of a section. */
function banner(title: string, payload: ReportPayload, colCount: number): string {
  const variantLine = formatVariantLine(payload.report_profile?.header, payload)
  return [
    `<tr><td colspan="${colCount}" style="background:${C.banner_bg};color:${C.banner_fg};font-family:${FONT_STACK};font-size:13pt;font-weight:700;letter-spacing:0.04em;padding:9px 12px;text-transform:uppercase;">${esc(title)}</td></tr>`,
    `<tr><td colspan="${colCount}" style="background:${C.variant_bg};color:${C.variant_fg};font-family:${FONT_STACK};font-size:10pt;font-style:italic;padding:6px 12px;border-bottom:1px solid ${C.border_strong};">Variant: ${esc(variantLine || '—')}</td></tr>`,
  ].join('')
}

/** Sub-section bar — a tinted bold row labelling the block beneath it. */
function subBand(title: string, colCount: number): string {
  return `<tr><td colspan="${colCount}" style="background:${C.sub_bg};color:${C.sub_fg};font-family:${FONT_STACK};font-size:10.5pt;font-weight:700;letter-spacing:0.03em;padding:7px 10px;text-transform:uppercase;border-top:1px solid ${C.border_strong};border-bottom:1px solid ${C.border};">${esc(title)}</td></tr>`
}

/** Spacer row — visual gap between blocks within a section. */
function spacer(colCount: number): string {
  return `<tr><td colspan="${colCount}" style="height:10px;border:none;background:transparent;line-height:10px;font-size:1px;">&nbsp;</td></tr>`
}

/** Table-header row (column labels). */
function theadRow(labels: string[]): string {
  const cells = labels
    .map(
      (l) =>
        `<th style="background:${C.thead_bg};color:${C.thead_fg};font-family:${FONT_STACK};font-size:10.5pt;font-weight:700;text-align:left;padding:7px 9px;border:1px solid ${C.border};">${esc(l)}</th>`,
    )
    .join('')
  return `<tr>${cells}</tr>`
}

interface CellOpts {
  href?: string | null
  mono?: boolean
  align?: 'left' | 'right' | 'center'
  bold?: boolean
  nowrap?: boolean
}

function td(value: unknown, opts: CellOpts = {}): string {
  const fam = opts.mono ? "Consolas, 'Courier New', monospace" : FONT_STACK
  const align = opts.align ?? 'left'
  const weight = opts.bold ? 700 : 400
  const whiteSpace = opts.nowrap ? 'nowrap' : 'normal'
  const display = value == null || value === '' ? '—' : value
  const href = safeExportHref(opts.href)
  const inner = href
    ? `<a href="${esc(href)}" rel="noopener noreferrer" style="color:${C.link};text-decoration:underline;">${esc(display)}</a>`
    : esc(display)
  return `<td style="font-family:${fam};font-size:10.5pt;font-weight:${weight};color:${C.body_fg};text-align:${align};vertical-align:top;white-space:${whiteSpace};word-wrap:break-word;overflow-wrap:break-word;padding:6px 9px;border:1px solid ${C.border};">${inner}</td>`
}

/** Body row — caller supplies pre-rendered <td> cells; we apply zebra fill. */
function bodyRow(index: number, cells: string): string {
  const bg = index % 2 === 0 ? C.row_a : C.row_b
  return `<tr style="background:${bg};">${cells}</tr>`
}

/** Two-column key/value row (label cell tinted, value cell plain). */
function kvRow(label: string, value: unknown, index: number): string {
  const bg = index % 2 === 0 ? C.row_a : C.row_b
  return [
    `<tr style="background:${bg};">`,
    `<td style="font-family:${FONT_STACK};font-size:10.5pt;font-weight:700;color:${C.thead_fg};text-align:left;vertical-align:top;padding:6px 9px;border:1px solid ${C.border};white-space:nowrap;">${esc(label)}</td>`,
    td(value, {}),
    '</tr>',
  ].join('')
}

interface ColSpec {
  /** px width — Excel converts to its own column units. */
  width: number
}

function colgroup(cols: ColSpec[]): string {
  return `<colgroup>${cols.map((c) => `<col style="width:${c.width}px;" />`).join('')}</colgroup>`
}

function wrap(inner: string): string {
  return [
    `<table style="border-collapse:collapse;font-family:${FONT_STACK};font-size:10.5pt;color:${C.body_fg};">`,
    inner,
    '</table>',
  ].join('')
}

/* ── 1. Population frequency (gnomAD) ───────────────────────────────────── */

export function htmlPopulation(
  payload: ReportPayload,
  detail: PopulationFrequencyDetail | null | undefined,
): string {
  const title = 'Population frequency (gnomAD)'
  if (!detail) {
    return wrap(
      [
        colgroup([{ width: 260 }, { width: 320 }]),
        banner(title, payload, 2),
        `<tr><td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;padding:14px 10px;color:${C.variant_fg};text-align:center;border:1px solid ${C.border};">Population data unavailable for this variant.</td></tr>`,
      ].join(''),
    )
  }

  const headerKV: Array<[string, unknown]> = [
    ['Source', detail.source],
    ['Dataset', detail.dataset],
    ['Variant ID', detail.variant_id],
    ['Sequencing type', detail.sequencing_type],
  ]
  if (detail.allele_frequency != null) headerKV.push(['Allele frequency', detail.allele_frequency])
  if (detail.allele_count != null) headerKV.push(['Allele count', detail.allele_count])
  if (detail.allele_number != null) headerKV.push(['Allele number', detail.allele_number])
  if (detail.homozygote_count != null) headerKV.push(['Homozygotes', detail.homozygote_count])
  if (detail.popmax_frequency != null) {
    headerKV.push(['Popmax frequency', detail.popmax_frequency])
    if (detail.popmax_population) headerKV.push(['Popmax population', detail.popmax_population])
  }

  const parts: string[] = [colgroup([{ width: 220 }, { width: 380 }]), banner(title, payload, 2)]
  parts.push(subBand('Summary', 2))
  parts.push(...headerKV.map(([k, v], i) => kvRow(k, v, i)))

  if (detail.genetic_ancestry_groups.length > 0) {
    parts.push(spacer(2))
    // Re-do colgroup for 5-col block — Excel honours the widest colgroup span.
    // We keep the table's first colgroup but the 5-col rows render fine without
    // a second colgroup; Excel auto-sizes the extras.
    parts.push(subBand('Genetic ancestry groups', 5))
    parts.push(theadRow(['Group', 'Allele count', 'Allele number', 'Allele frequency', 'Homozygotes']))
    detail.genetic_ancestry_groups.forEach((g, i) => {
      parts.push(
        bodyRow(
          i,
          td(g.id) +
            td(g.allele_count, { align: 'right' }) +
            td(g.allele_number, { align: 'right' }) +
            td(g.allele_frequency, { align: 'right', mono: true }) +
            td(g.homozygote_count, { align: 'right' }),
        ),
      )
    })
  }

  if (detail.flags.length > 0) {
    parts.push(spacer(2))
    parts.push(subBand('Flags', 1))
    detail.flags.forEach((f, i) => parts.push(bodyRow(i, td(f))))
  }
  if (detail.warnings.length > 0) {
    parts.push(spacer(2))
    parts.push(subBand('Warnings', 1))
    detail.warnings.forEach((w, i) => parts.push(bodyRow(i, td(w))))
  }
  if (detail.source_url) {
    parts.push(spacer(2))
    parts.push(bodyRow(0, td('Source URL', { bold: true }) + td(detail.source_url, { href: detail.source_url, mono: true })))
  }
  return wrap(parts.join(''))
}

/* ── 2. Evidence by source ─────────────────────────────────────────────── */

export function htmlEvidenceBySource(
  payload: ReportPayload,
  inSilico: InSilicoPredictions | null | undefined,
  acmg: AcmgCriteriaScaffold | null | undefined,
  evidenceRows: Array<{ source: string; status: string; summary: Record<string, unknown> }>,
): string {
  const title = 'Evidence by source'
  const parts: string[] = [
    colgroup([{ width: 170 }, { width: 110 }, { width: 110 }, { width: 360 }]),
    banner(title, payload, 4),
  ]

  if (inSilico && inSilico.cards.length > 0) {
    parts.push(subBand('In-silico predictions', 4))
    parts.push(theadRow(['Predictor', 'Score', 'Threshold', 'Verdict']))
    inSilico.cards.forEach((c, i) => {
      parts.push(
        bodyRow(
          i,
          td(c.name, { bold: true }) +
            td(c.score, { mono: true, align: 'right' }) +
            td(c.threshold, { mono: true, align: 'right' }) +
            td(c.verdict_label ?? c.verdict),
        ),
      )
    })
    if (inSilico.consensus_note) {
      parts.push(
        bodyRow(
          inSilico.cards.length,
          `<td colspan="4" style="font-family:${FONT_STACK};font-size:10.5pt;font-style:italic;color:${C.variant_fg};padding:6px 9px;border:1px solid ${C.border};">${esc('Consensus: ' + inSilico.consensus_note)}</td>`,
        ),
      )
    }
  }

  if (evidenceRows.length > 0) {
    if (inSilico && inSilico.cards.length > 0) parts.push(spacer(4))
    parts.push(subBand('Per-source detail', 3))
    parts.push(theadRow(['Source', 'Status', 'Summary']))
    evidenceRows.forEach((e, i) => {
      const summary = Object.entries(e.summary)
        .map(([k, v]) => `${k} = ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
        .join(' · ')
      parts.push(
        bodyRow(
          i,
          `<td style="font-family:${FONT_STACK};font-size:10.5pt;font-weight:700;color:${C.body_fg};vertical-align:top;padding:6px 9px;border:1px solid ${C.border};">${esc(e.source)}</td>` +
            td(e.status) +
            `<td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;color:${C.body_fg};vertical-align:top;white-space:normal;word-wrap:break-word;padding:6px 9px;border:1px solid ${C.border};">${esc(summary || '—')}</td>`,
        ),
      )
    })
  }

  if (acmg && acmg.criteria.length > 0) {
    parts.push(spacer(4))
    parts.push(subBand('ACMG criteria', 3))
    parts.push(theadRow(['Code', 'Verdict', 'Note']))
    acmg.criteria.forEach((c, i) => {
      parts.push(
        bodyRow(
          i,
          td(c.code, { mono: true, bold: true }) +
            td(c.verdict) +
            `<td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;color:${C.body_fg};vertical-align:top;white-space:normal;word-wrap:break-word;padding:6px 9px;border:1px solid ${C.border};">${esc(c.note ?? '—')}</td>`,
        ),
      )
    })
    if (acmg.disclaimer) {
      parts.push(
        `<tr><td colspan="4" style="font-family:${FONT_STACK};font-size:9.5pt;font-style:italic;color:${C.variant_fg};padding:8px 10px;border:1px solid ${C.border};background:${C.variant_bg};">${esc(acmg.disclaimer)}</td></tr>`,
      )
    }
  }

  return wrap(parts.join(''))
}

/* ── 3. Gene context snapshot (+ Locus) ─────────────────────────────────── */

export function htmlGeneContextSnapshot(
  payload: ReportPayload,
  snapshot: GeneContextSnapshot | null | undefined,
  locus: LocusContext | null | undefined,
): string {
  const title = 'Gene context snapshot'
  const parts: string[] = [
    colgroup([
      { width: 90 },
      { width: 110 },
      { width: 110 },
      { width: 130 },
      { width: 130 },
      { width: 110 },
    ]),
    banner(title, payload, 6),
  ]

  if (snapshot) {
    parts.push(subBand('Transcript summary', 6))
    const kv: Array<[string, unknown]> = []
    kv.push(['Gene', snapshot.gene])
    if (snapshot.transcript) kv.push(['Transcript', snapshot.transcript])
    if (snapshot.genome_build) kv.push(['Genome build', snapshot.genome_build])
    if (snapshot.strand) kv.push(['Strand', snapshot.strand])
    if (snapshot.gene_length != null) kv.push(['Gene length (bp)', snapshot.gene_length])
    kv.push(['Exons', snapshot.exons.length])
    if (snapshot.variant?.hgvs_c) kv.push(['Variant cDNA', snapshot.variant.hgvs_c])
    if (snapshot.variant?.hgvs_p) kv.push(['Variant protein', snapshot.variant.hgvs_p])
    if (snapshot.variant?.genomic_hg38) kv.push(['Genomic (GRCh38)', snapshot.variant.genomic_hg38])
    kv.forEach(([k, v], i) => {
      const bg = i % 2 === 0 ? C.row_a : C.row_b
      parts.push(
        `<tr style="background:${bg};">` +
          `<td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;font-weight:700;color:${C.thead_fg};vertical-align:top;padding:6px 9px;border:1px solid ${C.border};white-space:nowrap;">${esc(k)}</td>` +
          `<td colspan="4" style="font-family:${FONT_STACK};font-size:10.5pt;color:${C.body_fg};vertical-align:top;padding:6px 9px;border:1px solid ${C.border};">${esc(v == null || v === '' ? '—' : v)}</td>` +
          '</tr>',
      )
    })

    if (snapshot.exons.length > 0) {
      parts.push(spacer(6))
      parts.push(subBand('Exon table', 6))
      parts.push(theadRow(['Exon #', 'CDS start', 'CDS end', 'Genomic start', 'Genomic end', 'Length (bp)']))
      snapshot.exons.forEach((ex, i) => {
        parts.push(
          bodyRow(
            i,
            td(ex.number, { align: 'right', mono: true, bold: true }) +
              td(ex.cds_start ?? '—', { align: 'right', mono: true }) +
              td(ex.cds_end ?? '—', { align: 'right', mono: true }) +
              td(ex.genomic_start ?? '—', { align: 'right', mono: true }) +
              td(ex.genomic_end ?? '—', { align: 'right', mono: true }) +
              td(ex.genomic_length ?? '—', { align: 'right', mono: true }),
          ),
        )
      })
    }
  }

  if (locus && locus.nearby_variants.length > 0) {
    parts.push(spacer(6))
    parts.push(subBand('Locus context — nearby ClinVar variants', 6))
    if (locus.coords) {
      parts.push(
        `<tr><td colspan="6" style="font-family:${FONT_STACK};font-size:10pt;font-style:italic;color:${C.variant_fg};padding:6px 9px;border:1px solid ${C.border};background:${C.variant_bg};">Window: ${esc(locus.coords)}</td></tr>`,
      )
    }
    parts.push(theadRow(['CDS offset', 'HGVS', 'Protein change', 'Classification', 'ClinVar ID', '']))
    locus.nearby_variants.forEach((v, i) => {
      parts.push(
        bodyRow(
          i,
          td(v.cds_pos, { align: 'right', mono: true }) +
            td(v.hgvs, { mono: true }) +
            td(v.protein_change ?? '—', { mono: true }) +
            td(v.classification) +
            td(v.clinvar_id ?? '—', { mono: true }) +
            td(''),
        ),
      )
    })
  }

  return wrap(parts.join(''))
}

/* ── 4. Gene context & associated conditions ───────────────────────────── */

export function htmlDiseaseAndConditions(
  payload: ReportPayload,
  curated: CuratedVariantsDistribution | null | undefined,
  conditions: AssociatedCondition[] | undefined,
): string {
  const title = 'Gene context & associated conditions'
  const parts: string[] = []
  const exportableConditions = productExportFacts(conditions)

  // Pivot the curated table first so we know the column count.
  let curatedBlock = ''
  let curatedColCount = 0
  if (curated && Object.keys(curated.cells).length > 0) {
    const cellEntries = Object.entries(curated.cells)
    const classifications: string[] = []
    const columns: string[] = []
    for (const [key] of cellEntries) {
      const [cls, col] = key.split('|')
      if (cls && !classifications.includes(cls)) classifications.push(cls)
      if (col && !columns.includes(col)) columns.push(col)
    }
    if (classifications.length > 0 && columns.length > 0) {
      curatedColCount = columns.length + 2 // classification col + total col
      const rows: string[] = []
      rows.push(theadRow(['Classification', ...columns, 'Total']))
      classifications.forEach((cls, i) => {
        const cells = columns.map((col) => curated.cells[`${cls}|${col}`] ?? '—')
        rows.push(
          bodyRow(
            i,
            td(cls, { bold: true }) +
              cells.map((c) => td(c, { align: 'right', mono: true })).join('') +
              td(curated.row_totals?.[cls] ?? '—', { align: 'right', mono: true, bold: true }),
          ),
        )
      })
      curatedBlock = rows.join('')
    }
  }

  // Outer column count = max(curated, conditions table=6).
  const outerCols = Math.max(curatedColCount, 6)
  parts.push(banner(title, payload, outerCols))

  if (curatedBlock) {
    parts.push(subBand('Curated variants distribution', outerCols))
    if (curated?.subtitle) {
      parts.push(
        `<tr><td colspan="${outerCols}" style="font-family:${FONT_STACK};font-size:10pt;font-style:italic;color:${C.variant_fg};padding:6px 9px;border:1px solid ${C.border};background:${C.variant_bg};">Source: ${esc(curated.subtitle)} · Total: ${esc(curated?.total ?? '')}</td></tr>`,
      )
    }
    parts.push(curatedBlock)
    if (curated?.reading) {
      parts.push(
        `<tr><td colspan="${outerCols}" style="font-family:${FONT_STACK};font-size:10pt;color:${C.variant_fg};padding:8px 10px;border:1px solid ${C.border};background:${C.row_b};font-style:italic;">${esc(curated.reading)}</td></tr>`,
      )
    }
  }

  if (exportableConditions.length > 0) {
    if (curatedBlock) parts.push(spacer(outerCols))
    parts.push(subBand('Associated conditions', 6))
    parts.push(theadRow(['Condition', 'Cases', 'Evidence', 'Inheritance', 'Source ID', 'Sources']))
    exportableConditions.forEach((c, i) => {
      parts.push(
        bodyRow(
          i,
          td(c.name, { bold: true }) +
            td(c.case_count, { align: 'right', mono: true }) +
            td(c.evidence_level) +
            td(c.inheritance) +
            td(c.db_tag ?? '—', { mono: true }) +
            td(c.source_list ?? c.source),
        ),
      )
    })
  }

  if (!curatedBlock && exportableConditions.length === 0) {
    parts.push(
      `<tr><td colspan="${outerCols}" style="font-family:${FONT_STACK};font-size:10.5pt;padding:14px 10px;color:${C.variant_fg};text-align:center;border:1px solid ${C.border};">No curated condition data available.</td></tr>`,
    )
  }

  return wrap(parts.join(''))
}

/* ── 5. Publication literature ─────────────────────────────────────────── */

export function htmlPublications(
  payload: ReportPayload,
  literature: PublicationLiterature | null | undefined,
): string {
  const title = 'Publication literature'
  const cols: ColSpec[] = [
    { width: 80 }, // PMID
    { width: 360 }, // Title
    { width: 200 }, // Authors
    { width: 160 }, // Journal
    { width: 55 }, // Year
    { width: 110 }, // URL
    { width: 160 }, // Snippet status
  ]

  const articles = literature?.articles ?? payload.pubmed_articles ?? []
  if (articles.length === 0) {
    return wrap(
      [
        colgroup(cols),
        banner(title, payload, 7),
        `<tr><td colspan="7" style="font-family:${FONT_STACK};font-size:10.5pt;padding:14px 10px;color:${C.variant_fg};text-align:center;border:1px solid ${C.border};">No publications available.</td></tr>`,
      ].join(''),
    )
  }

  const parts: string[] = [colgroup(cols), banner(title, payload, 7)]
  if (literature) {
    parts.push(
      `<tr><td colspan="7" style="font-family:${FONT_STACK};font-size:10pt;font-style:italic;color:${C.variant_fg};padding:6px 12px;border:1px solid ${C.border};background:${C.variant_bg};">Showing ${esc(literature.shown_count)} of ${esc(literature.total_count)} publications</td></tr>`,
    )
  }
  parts.push(theadRow(['PMID', 'Title', 'Authors', 'Journal', 'Year', 'URL', 'Snippet status']))
  articles.forEach((a, i) => {
    parts.push(
      bodyRow(
        i,
        td(a.pmid, { mono: true, nowrap: true }) +
          td(a.title, { href: a.url, bold: true }) +
          td(a.authors) +
          td(a.journal) +
          td(a.year, { align: 'right', mono: true, nowrap: true }) +
          td(a.url, { href: a.url, mono: true }) +
          td('snippet_status' in a ? a.snippet_status ?? '—' : '—'),
      ),
    )
  })

  if (literature && literature.publication_timeline.publications_by_year.length > 0) {
    parts.push(spacer(7))
    parts.push(subBand('Publications by year', 2))
    parts.push(theadRow(['Year', 'Count']))
    literature.publication_timeline.publications_by_year.forEach((p, i) => {
      parts.push(bodyRow(i, td(p.year, { mono: true, align: 'right' }) + td(p.count, { align: 'right', mono: true })))
    })
    parts.push(
      bodyRow(
        literature.publication_timeline.publications_by_year.length,
        td('Undated total', { bold: true }) +
          td(literature.publication_timeline.total_without_year, { align: 'right', mono: true }),
      ),
    )
  }

  return wrap(parts.join(''))
}

/* ── 6. Active trials & approved therapies ─────────────────────────────── */

export function htmlTrials(payload: ReportPayload, trials: TrialMatch[]): string {
  const title = 'Active trials & approved therapies'
  const cols: ColSpec[] = [
    { width: 90 }, // NCT
    { width: 130 }, // Status
    { width: 90 }, // Phase
    { width: 110 }, // Match
    { width: 280 }, // Title
    { width: 200 }, // Conditions
    { width: 200 }, // Interventions
    { width: 200 }, // Locations
    { width: 110 }, // URL
  ]

  if (!trials || trials.length === 0) {
    return wrap(
      [
        colgroup(cols),
        banner(title, payload, 9),
        `<tr><td colspan="9" style="font-family:${FONT_STACK};font-size:10.5pt;padding:14px 10px;color:${C.variant_fg};text-align:center;border:1px solid ${C.border};">No clinical trial records.</td></tr>`,
      ].join(''),
    )
  }

  const parts: string[] = [colgroup(cols), banner(title, payload, 9)]
  parts.push(
    `<tr><td colspan="9" style="font-family:${FONT_STACK};font-size:10pt;font-style:italic;color:${C.variant_fg};padding:6px 12px;border:1px solid ${C.border};background:${C.variant_bg};">${esc(trials.length)} ClinicalTrials.gov record${trials.length === 1 ? '' : 's'}</td></tr>`,
  )
  parts.push(
    theadRow(['NCT', 'Status', 'Phase', 'Match level', 'Title', 'Conditions', 'Interventions', 'Locations', 'URL']),
  )
  trials.forEach((t, i) => {
    parts.push(
      bodyRow(
        i,
        td(t.nct_id, { mono: true, nowrap: true, href: t.source_url }) +
          td(t.status ?? '—') +
          td(t.phase ?? '—') +
          td(t.match_level) +
          td(t.title, { href: t.source_url, bold: true }) +
          td(joinPipes(t.conditions)) +
          td(joinPipes(t.interventions)) +
          td(joinPipes(t.locations)) +
          td(t.source_url, { href: t.source_url, mono: true }),
      ),
    )
  })

  return wrap(parts.join(''))
}

/* ── 7. AI evidence summary ────────────────────────────────────────────── */

export function htmlAISummary(payload: ReportPayload): string {
  const title = 'AI evidence summary'
  const parts: string[] = [colgroup([{ width: 180 }, { width: 540 }]), banner(title, payload, 2)]
  parts.push(kvRow('Mode', 'deterministic | cited', 0))
  if (payload.ai_clinical_summary) {
    parts.push(
      `<tr style="background:${C.row_b};"><td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;font-weight:700;color:${C.thead_fg};padding:8px 9px;border:1px solid ${C.border};">Clinical summary</td></tr>`,
      `<tr style="background:${C.row_a};"><td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;color:${C.body_fg};vertical-align:top;padding:10px 12px;border:1px solid ${C.border};line-height:1.55;white-space:normal;word-wrap:break-word;">${esc(payload.ai_clinical_summary)}</td></tr>`,
    )
  }
  const interp = payload.report_profile?.interpretation_summary
  if (interp?.text) {
    parts.push(
      `<tr style="background:${C.row_b};"><td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;font-weight:700;color:${C.thead_fg};padding:8px 9px;border:1px solid ${C.border};">Interpretation (${esc(interp.mode)})</td></tr>`,
      `<tr style="background:${C.row_a};"><td colspan="2" style="font-family:${FONT_STACK};font-size:10.5pt;color:${C.body_fg};vertical-align:top;padding:10px 12px;border:1px solid ${C.border};line-height:1.55;white-space:normal;word-wrap:break-word;">${esc(interp.text)}</td></tr>`,
    )
  }
  return wrap(parts.join(''))
}
