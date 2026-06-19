import { type ReactNode } from 'react'
import Link from 'next/link'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import { IconCalendar, IconEye, IconShare } from '@/components/icons/Icon'
import type { LookupResponse, ReportPayload, VariantSummaryRow } from '@/lib/backend'
import { SaveCurrentButton } from './VariantLibraryRail'

interface VariantHeaderViewMetric {
  view_count: number
  last_viewed?: string | null
}

interface VariantHeaderProps {
  payload: ReportPayload
  /** Full lookup response — threaded so the hero Save reuses the one library
   *  save path (no second, drifting save system). */
  data: LookupResponse
  query?: string
  viewMetric?: VariantHeaderViewMetric | null
  /** When provided, replaces the plain "Export PDF" button (e.g. the ExportMenu dropdown). */
  exportSlot?: ReactNode
}

interface CrossDbChip {
  label: string
  href: string
}

// Genoox/Franklin deliberately excluded — competitor, no outbound link.
function buildCrossDbChips(row: VariantSummaryRow | undefined, gene: string, ensemblGeneId?: string | null): CrossDbChip[] {
  const cdna = row?.transcript_hgvs?.split(':').pop() ?? ''
  const enc = encodeURIComponent(`${gene} ${cdna}`.trim())

  return [
    {
      label: 'ClinVar',
      href: `https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(gene + '[gene] ' + cdna)}`,
    },
    {
      label: 'gnomAD',
      href: ensemblGeneId
        ? `https://gnomad.broadinstitute.org/gene/${ensemblGeneId}?dataset=gnomad_r4`
        : `https://gnomad.broadinstitute.org/search?query=${encodeURIComponent(gene)}`,
    },
    {
      label: 'SpliceAI',
      href: 'https://spliceailookup.broadinstitute.org/',
    },
    {
      label: 'Ensembl',
      href: `https://www.ensembl.org/Homo_sapiens/Search/Results?q=${enc}`,
    },
    {
      label: 'PubMed',
      href: `https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(gene)}`,
    },
    {
      label: 'ClinicalTrials.gov',
      href: `https://clinicaltrials.gov/search?term=${encodeURIComponent(gene)}`,
    },
  ]
}

// GRCh38 RefSeq chromosome accessions — to build the genomic HGVS (g.) from the
// VCF triple. The g. nomenclature is derivable from the resolved coordinates.
const CHROM_NC: Record<string, string> = {
  '1': 'NC_000001.11', '2': 'NC_000002.12', '3': 'NC_000003.12', '4': 'NC_000004.12',
  '5': 'NC_000005.10', '6': 'NC_000006.12', '7': 'NC_000007.14', '8': 'NC_000008.11',
  '9': 'NC_000009.12', '10': 'NC_000010.11', '11': 'NC_000011.10', '12': 'NC_000012.12',
  '13': 'NC_000013.11', '14': 'NC_000014.9', '15': 'NC_000015.10', '16': 'NC_000016.10',
  '17': 'NC_000017.11', '18': 'NC_000018.10', '19': 'NC_000019.10', '20': 'NC_000020.11',
  '21': 'NC_000021.9', '22': 'NC_000022.11', X: 'NC_000023.11', Y: 'NC_000024.10', MT: 'NC_012920.1',
}

function deriveClassificationLabel(acmg: string | null | undefined): string | null {
  if (!acmg) return null
  const raw = acmg.toLowerCase()
  if (raw.includes('unavailable') || raw.includes('not found')) return null
  const first = acmg.split(/[—\-:]/)[0]?.trim()
  if (!first) return null
  const lc = first.toLowerCase()
  if (lc.includes('likely pathogenic')) return 'Likely pathogenic'
  if (lc.includes('likely benign')) return 'Likely benign'
  if (lc.includes('pathogenic')) return 'Pathogenic'
  if (lc.includes('benign')) return 'Benign'
  if (lc.includes('vus') || lc.includes('uncertain')) return 'VUS'
  return first
}

// "1-68444869-T-C" → "chr1:68,444,869" (1-based genomic coordinate).
function genomicCoordFromVcf(vcf: string | null): string | null {
  if (!vcf) return null
  const parts = vcf.split('-')
  if (parts.length < 2) return null
  const pos = Number(parts[1])
  if (!Number.isFinite(pos)) return null
  return `chr${parts[0]}:${pos.toLocaleString()}`
}

function readString(raw: unknown): string | null {
  return typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : null
}

type GeneContextVariantProjection = NonNullable<
  NonNullable<ReportPayload['report_profile']>['gene_context_snapshot']
>['variant']

function codonFromProjection(variant: GeneContextVariantProjection | null | undefined): string | null {
  if (!variant) return null
  const aaRef = readString(variant.aa_ref)
  const aaAlt = readString(variant.aa_alt)
  const number = typeof variant.codon_number === 'number' && variant.codon_number > 0 ? variant.codon_number : null
  if (aaRef && number && aaAlt) return `${aaRef}${number}${aaAlt}`
  if (number) return `codon ${number}`
  return null
}

function firstEnsemblTranscript(...aliases: Array<string[] | null | undefined>): string | null {
  for (const list of aliases) {
    const match = list?.find((alias) => /^ENST\d+(?:\.\d+)?$/i.test(alias.trim()))
    if (match) return match.trim()
  }
  return null
}

function firstEvidenceRsid(data: LookupResponse): string | null {
  for (const row of data.evidence) {
    const summaryRsid = readString(row.summary?.dbsnp_rsid)
    if (summaryRsid && /^rs\d+$/i.test(summaryRsid)) return summaryRsid
    const request = row.request_identity ?? {}
    const query = readString(request.query)
    if (query && /^rs\d+$/i.test(query)) return query
    const aliases = Array.isArray(request.variant_aliases) ? request.variant_aliases : []
    for (const alias of aliases) {
      const value = readString(alias)
      if (value && /^rs\d+$/i.test(value)) return value
    }
  }
  return null
}

function firstEvidenceEnsemblTranscript(data: LookupResponse): string | null {
  const matches: string[] = []
  for (const row of data.evidence) {
    const summaryTranscript = readString(row.summary?.transcript_id)
    if (summaryTranscript && /^ENST\d+(?:\.\d+)?$/i.test(summaryTranscript)) {
      matches.push(summaryTranscript)
    }
    const requestTranscript = readString(row.request_identity?.transcript_id)
    if (requestTranscript && /^ENST\d+(?:\.\d+)?$/i.test(requestTranscript)) {
      matches.push(requestTranscript)
    }
  }
  return matches.find((value) => /\.\d+$/.test(value)) ?? matches[0] ?? null
}

function unavailable(label = 'Unavailable') {
  return <span style={{ color: 'var(--ink-5)', fontFamily: 'var(--body)' }}>{label}</span>
}

function latestFetchedAt(data: LookupResponse): string | null {
  const dates = data.evidence
    .map((row) => row.fetched_at)
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .sort()
  return dates.at(-1) ?? null
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function VariantHeader({ payload, data, query, viewMetric, exportSlot }: VariantHeaderProps) {
  const row = payload.variant_summary_rows[0]
  // report_profile.header is richer than the summary row (it carries the protein
  // change + transcript even when the row's are null), so prefer it.
  const reportHeader = payload.report_profile?.header
  const geneContext = payload.report_profile?.gene_context_snapshot ?? null
  const geneContextVariant = geneContext?.variant ?? null
  const gene = row?.gene ?? reportHeader?.gene ?? '—'
  const proteinChange = reportHeader?.protein_change ?? row?.protein_change ?? geneContextVariant?.hgvs_p ?? null
  const transcriptHgvs = row?.transcript_hgvs ?? geneContextVariant?.hgvs_c ?? null
  const cdna = reportHeader?.cdna ?? transcriptHgvs?.split(':').pop() ?? geneContextVariant?.hgvs_c ?? null
  const transcriptId =
    reportHeader?.transcript ??
    geneContext?.transcript ??
    (transcriptHgvs?.includes(':') ? transcriptHgvs.split(':')[0] : null)
  const vcf = row?.genomic_hg38 ?? reportHeader?.genomic_hg38 ?? geneContextVariant?.genomic_hg38 ?? null
  const genomicCoord = genomicCoordFromVcf(vcf)
  // Exon comes from the molecular-context evidence row (same source MolecularContextBlock reads).
  const mcRow = data.evidence?.find((e) => e.source?.toLowerCase() === 'molecular_context')
  const mcSummary = (mcRow?.summary ?? null) as Record<string, unknown> | null
  const clinvarRow = data.evidence?.find((e) => e.source?.toLowerCase() === 'clinvar')
  const clinvarSummary = (clinvarRow?.summary ?? null) as Record<string, unknown> | null
  const consequence = row?.consequence ?? row?.variation_type ?? readString(clinvarSummary?.consequence)
  const exon =
    mcSummary && typeof mcSummary.exon === 'string'
      ? (mcSummary.exon as string)
      : geneContextVariant?.exon_number != null
        ? String(geneContextVariant.exon_number)
        : null
  const codon =
    mcSummary && typeof mcSummary.codon_change === 'string'
      ? (mcSummary.codon_change as string)
      : codonFromProjection(geneContextVariant)
  const dbsnpRsid = reportHeader?.dbsnp_rsid ?? readString(clinvarSummary?.dbsnp_rsid) ?? firstEvidenceRsid(data)
  const ensgId = reportHeader?.ensembl_gene_id ?? geneContext?.ensembl_gene_id ?? null
  const ensemblTranscript =
    reportHeader?.ensembl_transcript ??
    firstEnsemblTranscript(reportHeader?.transcript_aliases, geneContext?.transcript_aliases) ??
    firstEvidenceEnsemblTranscript(data)
  const maneSelect = reportHeader?.mane_select === true
  // Genomic HGVS (g.) - derived from the VCF triple + GRCh38 accession.
  const hgvsG = (() => {
    if (!vcf) return null
    const parts = vcf.split('-')
    const nc = CHROM_NC[parts[0]]
    if (!nc || parts.length < 4) return null
    return `${nc}:g.${parts[1]}${parts[2]}>${parts[3]}`
  })()
  const classificationLabel = deriveClassificationLabel(
    payload.report_profile?.header?.classification ??
      payload.report_profile?.acmg_worksheet?.classification ??
      payload.acmg_classification,
  )
  const chips = buildCrossDbChips(row, gene, ensgId)
  const latestFetch = latestFetchedAt(data)
  const updatedAt = reportHeader?.updated_at ?? latestFetch
  const viewCount = viewMetric?.view_count ?? reportHeader?.view_count ?? null

  return (
    <header>
      <nav
        aria-label="Breadcrumb"
        className="mb-4 flex items-center gap-2"
        style={{ fontSize: 12, color: 'var(--ink-4)' }}
      >
        <Link href="/" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
          Search
        </Link>
        <span style={{ color: 'var(--ink-5)' }}>/</span>
        <span>Variant report</span>
        <span style={{ color: 'var(--ink-5)' }}>/</span>
        <span style={{ fontFamily: 'var(--body)', fontVariantNumeric: 'tabular-nums', color: 'var(--ink-3)' }}>
          {query ?? transcriptHgvs ?? gene}
        </span>
      </nav>

      <section
        className="variant-header-card variant-header-slim mb-4"
        style={{
          background: 'var(--bg)',
          border: '0.5px solid var(--line)',
          borderRadius: 14,
          padding: '14px 20px',
        }}
      >
        {/* Row 1 — identity (DNA primary) on the left, classification hard-right */}
        <div className="vh-bar">
          <h1 className="vh-title">
            <span className="vh-gene">{gene}</span>
            {cdna && <span className="vh-cdna">{cdna}</span>}
            {proteinChange && <span className="vh-prot">{proteinChange}</span>}
          </h1>
          {classificationLabel && (
            <div className="vh-bar-right">
              <ClassificationBadge classification={classificationLabel} />
            </div>
          )}
        </div>

        {/* Row 2 — source status (left) + Save / Export / Share (right) */}
        <div className="vh-actions">
          <div className="vh-metrics" aria-label="Report source status">
            <span className="vh-metric" title="Report views recorded by the backend for this resolved variant">
              <IconEye />
              {typeof viewCount === 'number' ? (
                <>
                  <b>{viewCount.toLocaleString()}</b> views
                </>
              ) : (
                'Views unavailable'
              )}
            </span>
            <span className="vh-metric" title="Number of evidence source rows returned by the backend">
              <span style={{ color: 'var(--ink-4)', fontWeight: 400 }}>{data.evidence.length}</span> sources
            </span>
            <span className="vh-metric" title="Backend report update timestamp; falls back to the latest fetched_at source timestamp">
              <IconCalendar />
              {updatedAt ? (
                <>
                  Updated <span style={{ color: 'var(--ink-4)', fontWeight: 400 }}>{formatDate(updatedAt)}</span>
                </>
              ) : (
                'Source timestamps unavailable'
              )}
            </span>
          </div>
          <div className="v-tools">
            <SaveCurrentButton data={data} variant="hero" />
            {exportSlot}
            <ShareButton />
          </div>
        </div>

        {/* Row 3 — expandable details (full coords / HGVS / transcript / build) */}
        <details className="vh-details">
          <summary title="Show the full genomic coordinates, HGVS nomenclature, transcript, and build">
            <span className="vh-details-chev" aria-hidden>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" width="11" height="11">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </span>
            Variant details
          </summary>
          <div className="vh-details-body">
            <div className="vh-dl-cols">
              {/* Column 1 — nomenclature (6) */}
              <dl className="vh-dl">
                <dt title="HGVS coding-DNA nomenclature (c.)">HGVS c.</dt>
                <dd>{transcriptHgvs ?? cdna ?? '—'}</dd>
                <dt title="HGVS protein nomenclature (p.)">HGVS p.</dt>
                <dd>{proteinChange ?? unavailable()}</dd>
                <dt title="HGVS genomic nomenclature (g.) on GRCh38">HGVS g.</dt>
                <dd>{hgvsG ?? unavailable()}</dd>
                <dt title="The exon containing this variant">Exon</dt>
                <dd>{exon ?? unavailable()}</dd>
                <dt title="Codon change at the affected residue">Codon</dt>
                <dd>{codon ?? unavailable()}</dd>
                <dt>Consequence</dt>
                <dd>{consequence ?? '—'}</dd>
              </dl>
              {/* Column 2 — coordinates + identifiers (6) */}
              <dl className="vh-dl">
                <dt title="1-based genomic position (GRCh38)">Genomic</dt>
                <dd>{genomicCoord ? `${genomicCoord} · GRCh38` : '—'}</dd>
                <dt title="Variant Call Format — chrom-pos-ref-alt">VCF</dt>
                <dd>{vcf ?? '—'}</dd>
                <dt title="dbSNP reference SNP identifier">rsID</dt>
                <dd>
                  {dbsnpRsid ? (
                    <a href={`https://www.ncbi.nlm.nih.gov/snp/${dbsnpRsid}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--teal-deep)', textDecoration: 'none' }}>
                      {dbsnpRsid}
                    </a>
                  ) : unavailable()}
                </dd>
                <dt title="RefSeq (NCBI / Entrez) transcript">Transcript · RefSeq</dt>
                <dd>
                  {transcriptId ?? unavailable()}
                  {maneSelect && <span title="MANE Select transcript alias returned by backend gene-context data.">MANE Select</span>}
                </dd>
                <dt title="Ensembl gene identifier (ENSG)">Ensembl gene</dt>
                <dd>{ensgId ?? unavailable()}</dd>
                <dt title="Ensembl transcript identifier (ENST)">Ensembl transcript</dt>
                <dd>{ensemblTranscript ?? unavailable()}</dd>
              </dl>
            </div>
            <div className="v-jump" style={{ marginTop: 12 }}>
              <span className="v-jump-label">Open in</span>
              {chips.map((chip) => (
                <a
                  key={chip.label}
                  className="v-jump-chip"
                  href={chip.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={`Open this variant in ${chip.label}`}
                >
                  {chip.label} <span className="ext">↗</span>
                </a>
              ))}
            </div>
          </div>
        </details>

        <style>{`
          .variant-header-slim { display: flex; flex-direction: column; gap: 10px; }
          .vh-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
          .vh-title { margin: 0; display: inline-flex; align-items: baseline; flex-wrap: wrap; gap: 10px; min-width: 0; }
          .vh-gene { font-family: var(--display); font-weight: 400; font-size: 26px; line-height: 1.05; letter-spacing: -0.02em; color: var(--ink); }
          .vh-cdna { font-family: var(--body); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; font-size: 14px; font-weight: 500; color: var(--ink-2); }
          .vh-prot { font-family: var(--body); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; font-size: 13px; font-weight: 500; color: var(--ink-4); }
          .vh-bar-right { display: inline-flex; align-items: center; gap: 12px; flex-shrink: 0; }
          .vh-actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; }
          .vh-metrics { display: inline-flex; align-items: center; gap: 14px; flex-wrap: wrap; }
          .vh-metric { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--ink-3); }
          .vh-metric b { font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
          .vh-metric svg { width: 13px; height: 13px; color: var(--ink-4); flex-shrink: 0; }
          .vh-meta { display: inline-flex; align-items: center; gap: 8px; }
          .v-tools { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; }
          .vh-details { border-top: 0.5px solid var(--line); padding-top: 8px; }
          .vh-details > summary {
            list-style: none; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
            font-size: 11.5px; font-weight: 600; color: var(--ink-3); padding: 2px 0;
          }
          .vh-details > summary::-webkit-details-marker { display: none; }
          .vh-details > summary:hover { color: var(--ink); }
          .vh-details > summary:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); border-radius: 6px; }
          .vh-details-chev { display: inline-flex; transition: transform var(--dur-2) var(--ease-emphasized); color: var(--ink-4); }
          .vh-details[open] .vh-details-chev { transform: rotate(90deg); }
          .vh-details-body { margin-top: 10px; background: var(--bg-soft); border-radius: var(--r-md); padding: 12px 14px; }
          .vh-dl-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 28px; }
          .vh-dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 18px; margin: 0; align-content: start; }
          .vh-dl dt { font-size: 11px; color: var(--ink-4); align-self: baseline; }
          .vh-dl dt[title] { text-decoration: underline dotted; text-underline-offset: 3px; text-decoration-color: var(--ink-5); cursor: help; }
          .vh-dl dd { margin: 0; font-family: var(--mono); font-size: 12px; color: var(--ink-2); overflow-wrap: anywhere; display: inline-flex; align-items: center; gap: 6px; }
          .v-tool {
            transition: background var(--dur-1) var(--ease-standard),
                        border-color var(--dur-1) var(--ease-standard),
                        color var(--dur-1) var(--ease-standard);
          }
          .v-tool:hover { background: var(--bg-soft2) !important; border-color: var(--ink-5) !important; }
          .v-tool:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); border-color: var(--teal) !important; }
          .v-tool:active { transform: translateY(1px) scale(0.98); transition-duration: 80ms; }
          .v-jump-chip {
            transition: color var(--dur-1) var(--ease-standard),
                        border-color var(--dur-1) var(--ease-standard),
                        background var(--dur-1) var(--ease-standard);
          }
          .v-jump-chip:hover { color: var(--ink) !important; border-color: var(--ink-5) !important; background: var(--bg-soft2) !important; }
          .v-jump-chip:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(29,158,117,0.14); border-color: var(--teal) !important; }
          @media (max-width: 640px) {
            .variant-header-card { padding: 14px 14px !important; }
            .vh-gene { font-size: 23px; }
            .vh-bar-right { width: 100%; justify-content: space-between; }
            .vh-actions { align-items: flex-start; }
            .vh-dl-cols { grid-template-columns: 1fr; }
          }
        `}</style>
      </section>
    </header>
  )
}

function ShareButton() {
  return (
    <button
      type="button"
      className="v-tool"
      aria-label="Copy link to share"
      title="Copy a link to this exact report"
      onClick={(e) => {
        const btn = e.currentTarget
        if (typeof navigator !== 'undefined' && 'clipboard' in navigator) {
          void navigator.clipboard.writeText(window.location.href).then(() => {
            const span = btn.querySelector('span')
            if (span) {
              const prev = span.textContent
              span.textContent = 'Copied'
              setTimeout(() => {
                span.textContent = prev
              }, 2000)
            }
          })
        }
      }}
    >
      <IconShare />
      <span>Share</span>
    </button>
  )
}
