import { useState } from 'react'
import { ClassificationBadge } from '@/components/ui/ClassificationBadge'
import type { ReportPayload, VariantSummaryRow } from '@/lib/backend'

interface VariantHeaderProps {
  payload: ReportPayload
  query?: string
}

interface CrossDbChip {
  label: string
  href: string
}

// Genoox/Franklin deliberately excluded — competitor, no outbound link.
function buildCrossDbChips(row: VariantSummaryRow | undefined, gene: string): CrossDbChip[] {
  const cdna = row?.transcript_hgvs?.split(':').pop() ?? ''
  const enc = encodeURIComponent(`${gene} ${cdna}`.trim())

  return [
    {
      label: 'ClinVar',
      href: `https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(gene + '[gene] ' + cdna)}`,
    },
    {
      label: 'gnomAD',
      href: `https://gnomad.broadinstitute.org/gene/${ENSEMBL_BY_GENE[gene] ?? gene}?dataset=gnomad_r4`,
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

const ENSEMBL_BY_GENE: Record<string, string> = {
  RPE65: 'ENSG00000116745',
  USH2A: 'ENSG00000042781',
  ABCA4: 'ENSG00000198691',
  RPGR:  'ENSG00000156313',
  CNGA3: 'ENSG00000144348',
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

export function VariantHeader({ payload, query }: VariantHeaderProps) {
  const row = payload.variant_summary_rows[0]
  const gene = row?.gene ?? '—'
  const proteinChange = row?.protein_change ?? null
  const transcriptHgvs = row?.transcript_hgvs ?? null
  const genomic = row?.genomic_hg38 ?? null
  const consequence = row?.consequence ?? row?.variation_type ?? null
  const classificationLabel = deriveClassificationLabel(
    payload.report_profile?.header?.classification ??
      payload.report_profile?.acmg_worksheet?.classification ??
      payload.acmg_classification,
  )
  const [followed, setFollowed] = useState(false)
  const chips = buildCrossDbChips(row, gene)

  return (
    <header>
      <nav
        aria-label="Breadcrumb"
        className="mb-4 flex items-center gap-2"
        style={{ fontSize: 12, color: 'var(--ink-4)' }}
      >
        <a href="/" style={{ color: 'var(--ink-3)', textDecoration: 'none' }}>
          Search
        </a>
        <span style={{ color: 'var(--ink-5)' }}>/</span>
        <span>Variant report</span>
        <span style={{ color: 'var(--ink-5)' }}>/</span>
        <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-3)' }}>
          {query ?? transcriptHgvs ?? gene}
        </span>
      </nav>

      <section
        className="variant-header-card relative mb-4 overflow-hidden"
        style={{
          background: 'var(--bg)',
          border: '0.5px solid var(--line)',
          borderRadius: 14,
          padding: '28px 32px',
        }}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute right-0 top-0"
          style={{
            width: '50%',
            height: '100%',
            background:
              'radial-gradient(ellipse at top right, rgba(29,158,117,0.05), transparent 70%)',
          }}
        />
        <div className="variant-header-layout relative flex flex-wrap items-start justify-between gap-5">
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              className="mb-2 inline-flex items-center gap-1.5 uppercase"
              style={{
                fontSize: 10.5,
                fontWeight: 600,
                letterSpacing: '0.1em',
                color: 'var(--ink-4)',
              }}
            >
              <span
                style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--teal)' }}
              />
              Variant report · normalised from your query
            </div>
            <h1
              className="variant-title mb-1.5"
              style={{
                fontFamily: 'var(--display)',
                fontWeight: 600,
                fontSize: 36,
                lineHeight: 1.05,
                letterSpacing: '-0.02em',
                color: 'var(--ink)',
                margin: 0,
              }}
            >
              <span style={{ color: 'var(--teal-deep)' }}>{gene}</span>
              {proteinChange ? ` ${proteinChange}` : ''}
            </h1>
            <p
              className="variant-meta"
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 12.5,
                color: 'var(--ink-3)',
                margin: 0,
                overflowWrap: 'anywhere',
              }}
            >
              {[transcriptHgvs, genomic, consequence].filter(Boolean).map((part, i, arr) => (
                <span key={i}>
                  {part}
                  {i < arr.length - 1 && (
                    <span style={{ color: 'var(--ink-4)', padding: '0 6px' }}>·</span>
                  )}
                </span>
              ))}
            </p>

            <div className="v-jump">
              <span className="v-jump-label">Open in</span>
              {chips.map((chip) => (
                <a
                  key={chip.label}
                  className="v-jump-chip"
                  href={chip.href}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {chip.label} <span className="ext">↗</span>
                </a>
              ))}
            </div>
          </div>

          <div className="variant-header-actions flex flex-col items-end gap-2">
            <div className="flex flex-wrap justify-end gap-2">
              {classificationLabel && <ClassificationBadge classification={classificationLabel} />}
              {payload.clinical_phenotype && (
                <span className="badge subtle">
                  {payload.clinical_phenotype.split(/[,;/]/)[0]?.trim().slice(0, 22)}
                </span>
              )}
            </div>
            <div className="v-tools">
              <button
                type="button"
                className={followed ? 'v-tool followed' : 'v-tool'}
                aria-pressed={followed}
                onClick={() => setFollowed((v) => !v)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                  <path d="M10 21a2 2 0 0 0 4 0" />
                </svg>
                <span>{followed ? 'Following' : 'Follow'}</span>
              </button>
              <button type="button" className="v-tool" onClick={() => window.print()}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                <span>Export PDF</span>
              </button>
              <button
                type="button"
                className="v-tool"
                onClick={() => {
                  if (typeof navigator !== 'undefined' && 'clipboard' in navigator) {
                    void navigator.clipboard.writeText(window.location.href)
                  }
                }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                  <polyline points="16 6 12 2 8 6" />
                  <line x1="12" y1="2" x2="12" y2="15" />
                </svg>
                <span>Share</span>
              </button>
            </div>
          </div>
        </div>

        <style>{`
          @media (max-width: 640px) {
            .variant-header-card {
              padding: 22px 16px !important;
            }
            .variant-header-layout {
              display: block !important;
            }
            .variant-title {
              font-size: 30px !important;
              line-height: 1.08 !important;
            }
            .variant-meta {
              font-size: 11.5px !important;
              overflow-wrap: anywhere !important;
              word-break: normal !important;
            }
            .variant-header-actions {
              align-items: flex-start !important;
              margin-top: 16px;
              width: 100%;
            }
            .variant-header-actions > div {
              justify-content: flex-start !important;
            }
            .variant-header-actions .v-tools {
              width: 100%;
              justify-content: flex-start;
            }
            .variant-header-actions .v-tool {
              min-width: 0;
            }
          }
        `}</style>
      </section>
    </header>
  )
}
