/**
 * TSV serializers for the variant report sections.
 *
 * Each builder returns a tab-separated string with a section title, the
 * variant context line, a blank row, then header + data rows. Pasting into
 * Excel / Sheets splits cleanly into rows and columns; the header row
 * lands where a spreadsheet user expects it.
 *
 * Keep these defensive: every value should be passed through `cell()` to
 * collapse newlines and tabs (which would corrupt the row geometry).
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

/** Replace tabs/newlines (would break the TSV grid) with safe substitutes. */
function cell(value: unknown): string {
  if (value == null) return ''
  return String(value).replace(/\t/g, ' ').replace(/\r?\n/g, ' ').trim()
}

function row(...cells: unknown[]): string {
  return cells.map(cell).join('\t')
}

function blankRow(): string {
  return ''
}

function header(title: string, payload: ReportPayload): string {
  const h = payload.report_profile?.header
  const variantLine = formatVariantLine(h, payload)
  return [row('Section', title), row('Variant', variantLine), blankRow()].join('\n')
}

function formatVariantLine(
  h: VariantReportHeader | null | undefined,
  payload: ReportPayload,
): string {
  if (h) {
    return [h.gene, h.cdna, h.protein_change, h.genomic_hg38].filter(Boolean).join(' · ')
  }
  const row0 = payload.variant_summary_rows[0]
  if (row0) return [row0.gene, row0.transcript_hgvs, row0.protein_change].filter(Boolean).join(' · ')
  return ''
}

/* ── 1. Population frequency (gnomAD) ───────────────────────────────────── */

export function tsvPopulation(
  payload: ReportPayload,
  detail: PopulationFrequencyDetail | null | undefined,
): string {
  if (!detail) {
    return [header('Population frequency (gnomAD)', payload), row('Population data unavailable for this variant.')].join('\n')
  }
  const lines: string[] = [header('Population frequency (gnomAD)', payload)]
  lines.push(row('Field', 'Value'))
  lines.push(row('Source', detail.source))
  lines.push(row('Dataset', detail.dataset))
  lines.push(row('Variant ID', detail.variant_id))
  lines.push(row('Sequencing type', detail.sequencing_type))
  if (detail.allele_frequency != null) lines.push(row('Allele frequency', detail.allele_frequency))
  if (detail.allele_count != null) lines.push(row('Allele count', detail.allele_count))
  if (detail.allele_number != null) lines.push(row('Allele number', detail.allele_number))
  if (detail.homozygote_count != null) lines.push(row('Homozygotes', detail.homozygote_count))
  if (detail.popmax_frequency != null) {
    lines.push(row('Popmax frequency', detail.popmax_frequency))
    if (detail.popmax_population) lines.push(row('Popmax population', detail.popmax_population))
  }

  if (detail.genetic_ancestry_groups.length > 0) {
    lines.push(blankRow())
    lines.push(row('Genetic ancestry group', 'Allele count', 'Allele number', 'Allele frequency', 'Homozygotes'))
    for (const g of detail.genetic_ancestry_groups) {
      lines.push(row(g.id, g.allele_count, g.allele_number, g.allele_frequency, g.homozygote_count))
    }
  }

  if (detail.flags.length > 0) {
    lines.push(blankRow())
    lines.push(row('Flag'))
    for (const f of detail.flags) lines.push(row(f))
  }
  if (detail.warnings.length > 0) {
    lines.push(blankRow())
    lines.push(row('Warning'))
    for (const w of detail.warnings) lines.push(row(w))
  }
  if (detail.source_url) {
    lines.push(blankRow())
    lines.push(row('Source URL', detail.source_url))
  }
  return lines.join('\n')
}

/* ── 2. Evidence by source (in-silico + per-source + ACMG) ──────────────── */

export function tsvEvidenceBySource(
  payload: ReportPayload,
  inSilico: InSilicoPredictions | null | undefined,
  acmg: AcmgCriteriaScaffold | null | undefined,
  evidenceRows: Array<{ source: string; status: string; summary: Record<string, unknown> }>,
): string {
  const lines: string[] = [header('Evidence by source', payload)]

  if (inSilico && inSilico.cards.length > 0) {
    lines.push(row('In-silico predictions'))
    lines.push(row('Predictor', 'Score', 'Threshold', 'Verdict'))
    for (const c of inSilico.cards) {
      lines.push(row(c.name, c.score, c.threshold, c.verdict_label ?? c.verdict))
    }
    if (inSilico.consensus_note) {
      lines.push(blankRow())
      lines.push(row('Consensus', inSilico.consensus_note))
    }
    lines.push(blankRow())
  }

  if (evidenceRows.length > 0) {
    lines.push(row('Per-source detail'))
    lines.push(row('Source', 'Status', 'Summary'))
    for (const e of evidenceRows) {
      const summary = Object.entries(e.summary)
        .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`)
        .join(' · ')
      lines.push(row(e.source, e.status, summary))
    }
    lines.push(blankRow())
  }

  if (acmg && acmg.criteria.length > 0) {
    lines.push(row('ACMG criteria'))
    lines.push(row('Code', 'Verdict', 'Note'))
    for (const c of acmg.criteria) {
      lines.push(row(c.code, c.verdict, c.note ?? ''))
    }
    if (acmg.disclaimer) {
      lines.push(blankRow())
      lines.push(row('Disclaimer', acmg.disclaimer))
    }
  }

  return lines.join('\n')
}

/* ── 3. Gene context snapshot (+ merged Locus context) ──────────────────── */

export function tsvGeneContextSnapshot(
  payload: ReportPayload,
  snapshot: GeneContextSnapshot | null | undefined,
  locus: LocusContext | null | undefined,
): string {
  const lines: string[] = [header('Gene context snapshot', payload)]

  if (snapshot) {
    lines.push(row('Field', 'Value'))
    lines.push(row('Gene', snapshot.gene))
    if (snapshot.transcript) lines.push(row('Transcript', snapshot.transcript))
    if (snapshot.genome_build) lines.push(row('Genome build', snapshot.genome_build))
    if (snapshot.strand) lines.push(row('Strand', snapshot.strand))
    if (snapshot.gene_length != null) lines.push(row('Gene length (bp)', snapshot.gene_length))
    lines.push(row('Exons', snapshot.exons.length))
    if (snapshot.variant?.hgvs_c) lines.push(row('Variant cDNA', snapshot.variant.hgvs_c))
    if (snapshot.variant?.hgvs_p) lines.push(row('Variant protein', snapshot.variant.hgvs_p))
    if (snapshot.variant?.genomic_hg38) lines.push(row('Genomic (GRCh38)', snapshot.variant.genomic_hg38))
    if (snapshot.exons.length > 0) {
      lines.push(blankRow())
      lines.push(row('Exon table'))
      lines.push(row('Exon #', 'CDS start', 'CDS end', 'Genomic start', 'Genomic end', 'Length (bp)'))
      for (const ex of snapshot.exons) {
        lines.push(
          row(
            ex.number,
            ex.cds_start ?? '',
            ex.cds_end ?? '',
            ex.genomic_start ?? '',
            ex.genomic_end ?? '',
            ex.genomic_length ?? '',
          ),
        )
      }
    }
  }

  if (locus && locus.nearby_variants.length > 0) {
    lines.push(blankRow())
    lines.push(row('Locus context — nearby ClinVar variants'))
    if (locus.coords) lines.push(row('Window', locus.coords))
    lines.push(row('CDS offset', 'HGVS', 'Protein change', 'Classification', 'ClinVar ID'))
    for (const v of locus.nearby_variants) {
      lines.push(row(v.cds_pos, v.hgvs, v.protein_change ?? '', v.classification, v.clinvar_id ?? ''))
    }
  }

  return lines.join('\n')
}

/* ── 4. Gene context & associated conditions ────────────────────────────── */

export function tsvDiseaseAndConditions(
  payload: ReportPayload,
  curated: CuratedVariantsDistribution | null | undefined,
  conditions: AssociatedCondition[] | undefined,
): string {
  const lines: string[] = [header('Gene context & associated conditions', payload)]

  if (curated && Object.keys(curated.cells).length > 0) {
    lines.push(row('Curated variants distribution'))
    if (curated.subtitle) lines.push(row('Source', curated.subtitle))
    lines.push(row('Total', curated.total))

    // Cells are keyed `${classification}|${column}`. Pivot to a 2D table.
    const cellEntries = Object.entries(curated.cells)
    const classifications: string[] = []
    const columns: string[] = []
    for (const [key] of cellEntries) {
      const [cls, col] = key.split('|')
      if (cls && !classifications.includes(cls)) classifications.push(cls)
      if (col && !columns.includes(col)) columns.push(col)
    }
    if (classifications.length > 0 && columns.length > 0) {
      lines.push(blankRow())
      lines.push(row('Classification', ...columns, 'Total'))
      for (const cls of classifications) {
        const cells = columns.map((col) => curated.cells[`${cls}|${col}`] ?? '')
        lines.push(row(cls, ...cells, curated.row_totals?.[cls] ?? ''))
      }
    }
    if (curated.reading) {
      lines.push(blankRow())
      lines.push(row('Reading', curated.reading))
    }
    lines.push(blankRow())
  }

  if (conditions && conditions.length > 0) {
    lines.push(row('Associated conditions'))
    lines.push(row('Condition', 'Cases', 'Evidence', 'Inheritance', 'Source ID', 'Sources'))
    for (const c of conditions) {
      lines.push(
        row(
          c.name,
          c.case_count,
          c.evidence_level,
          c.inheritance,
          c.db_tag ?? '',
          c.source_list ?? c.source,
        ),
      )
    }
  }

  return lines.join('\n')
}

/* ── 5. Publication literature ──────────────────────────────────────────── */

export function tsvPublications(
  payload: ReportPayload,
  literature: PublicationLiterature | null | undefined,
): string {
  const lines: string[] = [header('Publication literature', payload)]
  if (!literature || literature.articles.length === 0) {
    const fallback = payload.pubmed_articles ?? []
    if (fallback.length === 0) {
      lines.push(row('No publications available.'))
      return lines.join('\n')
    }
    lines.push(row('Total', fallback.length))
    lines.push(blankRow())
    lines.push(row('PMID', 'Title', 'Authors', 'Journal', 'Year', 'URL'))
    for (const a of fallback) lines.push(row(a.pmid, a.title, a.authors, a.journal, a.year, a.url))
    return lines.join('\n')
  }

  lines.push(row('Total', literature.total_count))
  lines.push(row('Shown', literature.shown_count))
  lines.push(blankRow())
  lines.push(row('PMID', 'Title', 'Authors', 'Journal', 'Year', 'URL', 'Snippet status'))
  for (const a of literature.articles) {
    lines.push(row(a.pmid, a.title, a.authors, a.journal, a.year, a.url, a.snippet_status ?? ''))
  }

  if (literature.publication_timeline.publications_by_year.length > 0) {
    lines.push(blankRow())
    lines.push(row('Publications by year'))
    lines.push(row('Year', 'Count'))
    for (const p of literature.publication_timeline.publications_by_year) {
      lines.push(row(p.year, p.count))
    }
    lines.push(
      row(
        'Undated total',
        literature.publication_timeline.total_without_year,
      ),
    )
  }

  return lines.join('\n')
}

/* ── 6. Active trials & approved therapies ──────────────────────────────── */

export function tsvTrials(payload: ReportPayload, trials: TrialMatch[]): string {
  const lines: string[] = [header('Active trials & approved therapies', payload)]
  if (!trials || trials.length === 0) {
    lines.push(row('No clinical trial records.'))
    return lines.join('\n')
  }
  lines.push(row('Total', trials.length))
  lines.push(blankRow())
  lines.push(
    row('NCT', 'Status', 'Phase', 'Match level', 'Title', 'Conditions', 'Interventions', 'Locations', 'URL'),
  )
  for (const t of trials) {
    lines.push(
      row(
        t.nct_id,
        t.status ?? '',
        t.phase ?? '',
        t.match_level,
        t.title,
        t.conditions.join(' | '),
        t.interventions.join(' | '),
        t.locations.join(' | '),
        t.source_url,
      ),
    )
  }
  return lines.join('\n')
}

/* ── 7. AI evidence summary ─────────────────────────────────────────────── */

export function tsvAISummary(payload: ReportPayload): string {
  const lines: string[] = [header('AI evidence summary', payload)]
  lines.push(row('Mode', 'deterministic | cited'))
  if (payload.ai_clinical_summary) {
    lines.push(blankRow())
    lines.push(row('Summary', payload.ai_clinical_summary))
  }
  const interp = payload.report_profile?.interpretation_summary
  if (interp?.text) {
    lines.push(blankRow())
    lines.push(row('Interpretation mode', interp.mode))
    lines.push(row('Interpretation', interp.text))
  }
  return lines.join('\n')
}
