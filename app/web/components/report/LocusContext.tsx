'use client'
import { useState } from 'react'
import type {
  LocusContext as LocusContextData,
  NearbyVariant as NearbyVariantData,
  CodonCell as CodonCellData,
  ClassificationTier,
} from '@/lib/backend'

type ZoomLevel = 'gene' | 'exon' | 'codon'

interface NearbyVariantDisplay {
  left: number
  classification: 'p' | 'lp' | 'vus' | 'lb' | 'b'
  title: string
  queried?: boolean
}

interface CodonCellDisplay {
  aa: string
  dna: string
  dnaAlt?: string
  dnaPost?: string
  pos: number
  queried?: boolean
}

interface LocusContextProps {
  data?: LocusContextData | null
}

const LANE_TOPS: Record<NearbyVariantDisplay['classification'], string> = {
  p: '0%', lp: '25%', vus: '50%', lb: '75%', b: '100%',
}

const TIER_ABBREV: Record<ClassificationTier, NearbyVariantDisplay['classification']> = {
  pathogenic: 'p',
  likely_pathogenic: 'lp',
  vus: 'vus',
  likely_benign: 'lb',
  benign: 'b',
}

const TIER_LABEL: Record<ClassificationTier, string> = {
  pathogenic: 'Pathogenic',
  likely_pathogenic: 'Likely Pathogenic',
  vus: 'VUS',
  likely_benign: 'Likely Benign',
  benign: 'Benign',
}

const AA_1TO3: Record<string, string> = {
  A: 'Ala', R: 'Arg', N: 'Asn', D: 'Asp', C: 'Cys',
  E: 'Glu', Q: 'Gln', G: 'Gly', H: 'His', I: 'Ile',
  L: 'Leu', K: 'Lys', M: 'Met', F: 'Phe', P: 'Pro',
  S: 'Ser', T: 'Thr', W: 'Trp', Y: 'Tyr', V: 'Val',
}

function aa3(letter: string): string {
  return AA_1TO3[letter] ?? letter
}

// Position the variant dots across the lane. `widthScale` lets us spread
// further from the centre marker when zoomed out to the full gene view, and
// compress toward the centre at the exon view.
function mapNearby(items: NearbyVariantData[], widthScale: number): NearbyVariantDisplay[] {
  const span = items.reduce((acc, v) => Math.max(acc, Math.abs(v.cds_pos)), 0) || 1
  return items.map((v) => {
    const tierLabel = TIER_LABEL[v.classification]
    const queried = v.cds_pos === 0
    const titleParts = [v.hgvs]
    if (v.protein_change) titleParts.push(v.protein_change)
    if (queried) titleParts.push('queried')
    titleParts.push(tierLabel)
    return {
      left: 50 + (v.cds_pos / span) * 50 * widthScale,
      classification: TIER_ABBREV[v.classification],
      title: titleParts.join(' · '),
      queried,
    }
  })
}

function mapCodons(items: CodonCellData[]): CodonCellDisplay[] {
  return items.map((c) => {
    if (c.is_query && c.aa_alt && c.dna_alt) {
      const ref = c.dna_ref ?? ''
      const alt = c.dna_alt
      let diff = alt.length - 1
      for (let i = 0; i < alt.length; i++) {
        if (ref[i] !== alt[i]) {
          diff = i
          break
        }
      }
      return {
        aa: `${aa3(c.aa_ref)} → ${aa3(c.aa_alt)}`,
        dna: alt.slice(0, diff),
        dnaAlt: alt[diff],
        dnaPost: alt.slice(diff + 1),
        pos: c.codon_number,
        queried: true,
      }
    }
    return {
      aa: aa3(c.aa_ref),
      dna: c.dna_ref ?? '',
      pos: c.codon_number,
      queried: c.is_query,
    }
  })
}

const ZOOM_LEVELS: Array<{ id: ZoomLevel; label: string; hint: string }> = [
  { id: 'gene',  label: 'Gene',  hint: 'Full gene span — nearby variants only, no codons' },
  { id: 'exon',  label: 'Exon',  hint: 'Balanced view — variants in lanes and the codon strip together' },
  { id: 'codon', label: 'Codon', hint: 'Codon strip only — focus on the local protein neighbourhood' },
]

export function LocusContext({ data }: LocusContextProps) {
  // Default to the balanced 'exon' view (variants + codons together).
  const [zoom, setZoom] = useState<ZoomLevel>('exon')

  if (!data) {
    return (
      <p style={{ fontSize: 12.5, color: 'var(--ink-4)', margin: 0 }}>
        No locus context available for this variant.
      </p>
    )
  }

  const widthScale = zoom === 'gene' ? 1.4 : zoom === 'exon' ? 1.0 : 0.7
  const nearby = mapNearby(data.nearby_variants, widthScale)
  const codons = mapCodons(data.codon_strip)
  const coords = data.coords || `${data.gene} · ${data.centre_cdna}`
  const centreLabel = data.centre_cdna
  const workbenchHref = `/workbench?gene=${encodeURIComponent(data.gene)}&cdna=${encodeURIComponent(data.centre_cdna)}`

  const queried = nearby.find((v) => v.queried)
  const markerLeft = queried?.left ?? 50

  const showLanes = zoom !== 'codon'
  const showCodons = zoom !== 'gene'
  // When the codon strip is hidden the marker line shouldn't drop below the
  // lane track; clamp it to the lane row height so it doesn't trail off.
  const markerBottom = showCodons ? '-110px' : '0px'

  return (
    <div className="locus">
      <div className="locus-bar">
        <div className="locus-coords">{coords}</div>
        <div className="locus-zoom" role="group" aria-label="Zoom level">
          {ZOOM_LEVELS.map(({ id, label, hint }) => (
            <button
              key={id}
              type="button"
              className={zoom === id ? 'active' : ''}
              aria-pressed={zoom === id}
              title={hint}
              onClick={() => setZoom(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="locus-track">
        {showLanes && (
          <div className="locus-row variants">
            <span className="axis-label">ClinVar variants nearby</span>
            <div className="lane">
              <div className="lane-line p" /><span className="lane-label" style={{ top: '0%' }}>P</span>
              <div className="lane-line lp" /><span className="lane-label" style={{ top: '25%' }}>LP</span>
              <div className="lane-line vus" /><span className="lane-label" style={{ top: '50%' }}>VUS</span>
              <div className="lane-line lb" /><span className="lane-label" style={{ top: '75%' }}>LB</span>
              <div className="lane-line b" /><span className="lane-label" style={{ top: '100%' }}>B</span>

              {nearby
                .filter((v) => v.left >= -5 && v.left <= 105)
                .map((v, i) => (
                  <span
                    key={i}
                    className={`locus-dot ${v.classification}${v.queried ? ' queried' : ''}`}
                    style={{ left: `${v.left}%`, top: LANE_TOPS[v.classification] }}
                    title={v.title}
                  />
                ))}

              <div
                className="locus-marker"
                data-label={centreLabel}
                style={{ left: `${markerLeft}%`, bottom: markerBottom }}
              />
            </div>
          </div>
        )}

        {showCodons && (
          <div className="locus-row codons">
            {codons.map((c, i) => (
              <div key={i} className={c.queried ? 'codon queried' : 'codon'}>
                <span className="aa">{c.aa}</span>
                <span className="dna">
                  {c.dna}
                  {c.dnaAlt && <span className="alt">{c.dnaAlt}</span>}
                  {c.dnaPost}
                </span>
                <span className="pos">{c.pos}</span>
              </div>
            ))}
          </div>
        )}

        <div className="locus-legend">
          <div className="locus-legend-item"><span className="dot" style={{ background: 'var(--cls-path-dot)' }} />Pathogenic</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: 'var(--cls-lpath-dot)' }} />Likely Pathogenic</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: 'var(--cls-vus-dot)' }} />VUS</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: 'var(--cls-lben-dot)' }} />Likely Benign</div>
          <div className="locus-legend-item"><span className="dot" style={{ background: 'var(--cls-ben-dot)' }} />Benign</div>
        </div>

        <div className="locus-footer">
          <a className="locus-workbench-link" href={workbenchHref}>
            Open full sequence in Workbench ↗
          </a>
        </div>
      </div>
    </div>
  )
}
