'use client'
import { memo, useMemo, type CSSProperties } from 'react'
import type { AlleleMode } from '@/lib/backend'
import {
  classLabel,
  type ClinClass,
  type GeneWindowData,
} from '@/lib/workbench/gene-window'

/* ───────────────────────────────────────────────────────────────────────
   Protein view (GV-006) — the third detail mode, replacing the removed
   exon-only band. A protein backbone (aa 1 … protein_length) with
   domain/feature bars and a domain-aware ClinVar lollipop track. Coding
   ClinVar variants are projected to amino-acid coordinates
   (aa = ceil(cds_pos / 3)); splice/intronic records (string cds_pos) have
   no protein coordinate and are listed, not projected.

   Marker size is UNIFORM by design: ClinVar is a curated clinical-variation
   record set, not a cohort frequency table. Size must not imply patient
   frequency (plans/gene-viewer/{design,spec}.md; Codex Cross-Agent note
   2026-05-18 15:22). The ClinVar set is whatever the loaded window/payload
   carries (sample-bounded offline) — not gene-wide.
─────────────────────────────────────────────────────────────────────── */

interface ProteinViewProps {
  data: GeneWindowData
  alleleMode: AlleleMode
}

interface Lollipop {
  aa: number
  xPct: number
  lane: number
  cls: ClinClass
  kind: ProteinMarkerKind
  queried: boolean
  hgvsC: string
  hgvsP: string
  cv: string
}

type ProteinMarkerKind = 'missense' | 'truncating' | 'splice'

const CLASS_DOT_COLOR: Record<ClinClass, string> = {
  p: 'var(--cls-path-dot)',
  lp: 'var(--cls-lpath-dot)',
  vus: 'var(--cls-vus-dot)',
  lb: 'var(--cls-lben-dot)',
  b: 'var(--cls-ben-dot)',
}

interface ProteinDomainBar {
  aaStart: number
  aaEnd: number
  label: string
  short?: string
  source?: string
  accession?: string
  broadBackbone?: boolean
}

interface ProteinFeatureColor {
  fill: string
  stroke: string
  text: string
}

interface ProteinLegendFeature {
  key: string
  kindLabel: string
  short: string
  label: string
  aaStart: number
  aaEnd: number
  color: ProteinFeatureColor
}

/** Consecutive variants closer than this (in % of the backbone) are stacked
 *  into higher lanes so heads + stems do not overlap. Heuristic — the view
 *  is responsive and cannot measure px without an observer. */
const LANE_GAP_PCT = 3.4
const MAX_LANES = 4

function proteinMarkerKind(hgvsC: string, hgvsP: string, splice = false): ProteinMarkerKind {
  const text = `${hgvsC} ${hgvsP}`.toLowerCase()
  if (splice || text.includes('splice') || /c\.[^\s]*[+-][12](?:\D|$)/.test(text)) {
    return 'splice'
  }
  if (
    text.includes('ter') ||
    text.includes('*') ||
    text.includes('fs') ||
    text.includes('frameshift') ||
    text.includes('stop') ||
    text.includes('nonsense') ||
    text.includes('trunc')
  ) {
    return 'truncating'
  }
  return 'missense'
}

function lollipopStyle(cls: ClinClass): CSSProperties {
  return {
    '--sv-pv-pop-color': CLASS_DOT_COLOR[cls] ?? 'var(--cls-na-dot)',
  } as CSSProperties
}

function hashString(value: string): number {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

function domainPaletteKey(feature: Pick<ProteinDomainBar, 'short' | 'label'>): string {
  const short = feature.short?.trim().toLowerCase() ?? ''
  if (short && short.length <= 18 && !short.endsWith('...')) return short
  return feature.label.trim().toLowerCase()
}

function domainPaletteColor(feature: Pick<ProteinDomainBar, 'short' | 'label' | 'broadBackbone'>): ProteinFeatureColor {
  if (feature.broadBackbone) {
    return {
      fill: 'rgba(92, 107, 122, 0.12)',
      stroke: 'rgba(92, 107, 122, 0.44)',
      text: 'var(--ink-2)',
    }
  }
  const palette = [
    ['rgba(44, 123, 182, 0.18)', 'rgba(44, 123, 182, 0.58)', 'rgb(22, 78, 121)'],
    ['rgba(86, 160, 103, 0.18)', 'rgba(72, 137, 87, 0.58)', 'rgb(39, 96, 55)'],
    ['rgba(196, 118, 62, 0.18)', 'rgba(173, 93, 42, 0.58)', 'rgb(123, 66, 29)'],
    ['rgba(129, 102, 181, 0.18)', 'rgba(111, 82, 164, 0.58)', 'rgb(78, 56, 125)'],
    ['rgba(196, 87, 112, 0.16)', 'rgba(174, 66, 93, 0.56)', 'rgb(125, 45, 65)'],
    ['rgba(37, 151, 143, 0.16)', 'rgba(26, 126, 120, 0.56)', 'rgb(20, 92, 88)'],
    ['rgba(184, 143, 50, 0.18)', 'rgba(158, 118, 31, 0.58)', 'rgb(113, 83, 20)'],
    ['rgba(89, 111, 173, 0.17)', 'rgba(70, 91, 151, 0.55)', 'rgb(50, 66, 112)'],
    ['rgba(159, 104, 70, 0.17)', 'rgba(138, 82, 49, 0.55)', 'rgb(96, 58, 37)'],
    ['rgba(90, 138, 156, 0.16)', 'rgba(70, 116, 135, 0.54)', 'rgb(47, 83, 98)'],
  ] as const
  const [fill, stroke, text] = palette[hashString(domainPaletteKey(feature)) % palette.length]
  return { fill, stroke, text }
}

function shortFeatureLabel(label: string): string {
  return label.length > 34 ? `${label.slice(0, 31)}...` : label
}

function domainLabelForWidth(domain: ProteinDomainBar, widthPct: number): string {
  if (widthPct < 2.4) return ''
  const label = domain.short || shortFeatureLabel(domain.label)
  if (widthPct >= 5) return label
  return label.length > 6 ? `${label.slice(0, 5)}...` : label
}

function groupLegendFeatures(features: ProteinLegendFeature[]): Array<{
  key: string
  kindLabel: string
  short: string
  label: string
  coordLabel: string
  count: number
  color: ProteinFeatureColor
  title: string
}> {
  const groups = new Map<string, ProteinLegendFeature[]>()
  features.forEach((feature) => {
    const groupKey = `${feature.kindLabel}|${feature.short}|${feature.label}`
    groups.set(groupKey, [...(groups.get(groupKey) ?? []), feature])
  })
  return Array.from(groups.entries()).map(([key, group]) => {
    const sorted = group.sort((a, b) => a.aaStart - b.aaStart || a.aaEnd - b.aaEnd)
    const min = Math.min(...sorted.map((feature) => feature.aaStart))
    const max = Math.max(...sorted.map((feature) => feature.aaEnd))
    const ranges = sorted
      .slice(0, 4)
      .map((feature) =>
        feature.aaStart === feature.aaEnd
          ? `aa ${feature.aaStart}`
          : `aa ${feature.aaStart}-${feature.aaEnd}`,
      )
      .join(', ')
    const overflow = sorted.length > 4 ? `, +${sorted.length - 4} more` : ''
    return {
      key,
      kindLabel: sorted[0].kindLabel,
      short: sorted[0].short,
      label: sorted[0].label,
      coordLabel: sorted.length === 1 ? ranges : `${sorted.length}x | aa ${min}-${max}`,
      count: sorted.length,
      color: sorted[0].color,
      title: `${sorted.map((feature) => `${feature.label} | aa ${feature.aaStart}-${feature.aaEnd}`).join('\n')}${overflow}`,
    }
  })
}

export const ProteinView = memo(function ProteinView({ data, alleleMode }: ProteinViewProps) {
  const product = alleleMode === 'variant' ? data.proteinProduct : null
  const referenceLen = Math.max(
    1,
    product?.referenceProteinLength ?? data.proteinLength ?? 0,
  )
  const effectiveLen = Math.max(
    0,
    product?.truncatesProtein
      ? (product.effectiveProteinLength ?? data.proteinLength)
      : data.proteinLength,
  )
  const protLen = product?.truncatesProtein ? referenceLen : Math.max(1, data.proteinLength || 0)
  const truncationStartAa =
    product?.truncatesProtein
      ? (product.stopCodon ?? Math.min(referenceLen, effectiveLen + 1))
      : null
  const clampAa = (aa: number) => Math.min(Math.max(aa, 1), protLen)
  const pct = (aa: number) => ((clampAa(aa) - 1) / Math.max(1, protLen - 1)) * 100
  const spanStyle = (aaStart: number, aaEnd: number) => {
    const left = pct(aaStart)
    return { left: `${left}%`, width: `${Math.max(0, pct(aaEnd) - left)}%` }
  }
  const scaleTicks = useMemo(() => {
    const ticks = [
      1,
      Math.round(protLen / 4),
      Math.round(protLen / 2),
      Math.round((3 * protLen) / 4),
      protLen,
    ].map((aa) => Math.min(Math.max(aa, 1), protLen))
    return Array.from(new Set(ticks)).sort((a, b) => a - b)
  }, [protLen])

  const qv = data.queriedVariant
  const { lollipops, splices } = useMemo(() => {
    const splices: GeneWindowData['clinvar'] = []
    const queriedAa = qv.codonNumber || Math.ceil(qv.cdsPos / 3) || 1
    const coding = data.clinvar
      .filter((v) => {
        if (typeof v.cdsPos !== 'number') {
          splices.push(v)
          return false
        }
        return true
      })
      .map((v) => ({
        v,
        aa: Math.ceil((v.cdsPos as number) / 3),
      }))
    const hasQueriedMarker = coding.some(
      ({ v, aa }) => v.queried || (v.hgvsC === qv.hgvsC && aa === queriedAa),
    )
    if (!hasQueriedMarker) {
      coding.push({
        v: {
          cdsPos: qv.cdsPos,
          hgvsC: qv.hgvsC,
          hgvsP: qv.hgvsP,
          cls: qv.classification,
          cv: 'queried',
          queried: true,
        },
        aa: queriedAa,
      })
    }
    coding.sort((a, b) => a.aa - b.aa)

    const laneTail: number[] = []
    const pops: Lollipop[] = coding.map(({ v, aa }) => {
      const xPct = pct(aa)
      let lane = 0
      while (
        lane < MAX_LANES - 1 &&
        laneTail[lane] != null &&
        xPct - laneTail[lane] < LANE_GAP_PCT
      ) {
        lane++
      }
      laneTail[lane] = xPct
      return {
        aa,
        xPct,
        lane,
        cls: v.cls,
        kind: proteinMarkerKind(v.hgvsC, v.hgvsP, Boolean(v.splice)),
        queried: Boolean(v.queried),
        hgvsC: v.hgvsC,
        hgvsP: v.hgvsP,
        cv: v.cv,
      }
    })
    return { lollipops: pops, splices }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, protLen])

  const { activeSites, membraneBinding, palmitoylation, signalPeptide } =
    data.proteinFeatures
  const hasSpecificUniProtFeatures =
    activeSites.length > 0 || membraneBinding.length > 0 || palmitoylation.length > 0 || Boolean(signalPeptide)

  // Prefer the protein-features domain list; fall back to the rich
  // top-level domain list (which may carry a short label). Normalized to a
  // uniform shape so the union does not leak into JSX.
  const domainBars = (
    data.proteinFeatures.domains.length
      ? data.proteinFeatures.domains
      : data.domains
  ).map((d) => ({
    aaStart: d.aaStart,
    aaEnd: d.aaEnd,
    label: d.label,
    short: (d as { shortLabel?: string }).shortLabel,
    broadBackbone: (d as { broadBackbone?: boolean }).broadBackbone,
  }))
    .filter((d) => !(d.broadBackbone && hasSpecificUniProtFeatures))

  const featureCount =
    domainBars.length +
    activeSites.length +
    membraneBinding.length +
    palmitoylation.length +
    (signalPeptide ? 1 : 0)

  return (
    <div className="sv-protein">
      <div className="sv-pv-head-row">
        <span className="sv-pv-title">Protein architecture &amp; features</span>
        <span className="sv-pv-meta">
          {data.gene} ·{' '}
          {product?.truncatesProtein
            ? `${effectiveLen} / ${referenceLen} aa`
            : `${protLen} aa`}{' '}
          ·{' '}
          {alleleMode === 'variant' ? 'variant-applied' : 'reference'} ·{' '}
          {product?.truncatesProtein ? `${product.label} · ` : ''}
          {featureCount} feature{featureCount === 1 ? '' : 's'} ·{' '}
          {lollipops.length} ClinVar record{lollipops.length === 1 ? '' : 's'}{' '}
          projected
          {splices.length ? ` (+${splices.length} splice/intronic)` : ''}
        </span>
      </div>

      <div className="sv-pv-stage">
        {/* Lollipop track (above the backbone) */}
        <div className="sv-pv-lollipops">
          {lollipops.map((p, i) => {
            const h = 20 + p.lane * 16
            const labelEdge =
              p.xPct < 18 ? ' edge-left' : p.xPct > 82 ? ' edge-right' : ''
            return (
              <div
                key={`${p.cv || p.hgvsC}-${p.hgvsP}-${p.aa}-${i}`}
                className="sv-pv-pop"
                style={{ left: `${p.xPct}%`, height: h, ...lollipopStyle(p.cls) }}
                title={`${p.hgvsC} · ${p.hgvsP} · ${classLabel(p.cls)}${
                  p.queried ? ' · queried' : ''
                }`}
              >
                <span className="sv-pv-stem" style={{ height: h }} />
                <span
                  className={`sv-pv-headdot ${p.cls} shape-${p.kind}${
                    p.queried ? ' queried' : ''
                  }`}
                />
                {p.queried && (
                  <span className={`sv-pv-poplabel${labelEdge}`}>
                    {p.hgvsC} · {p.hgvsP} (aa {p.aa})
                  </span>
                )}
              </div>
            )
          })}
        </div>

        {/* Backbone + domains + region features */}
        <div className="sv-pv-backbone">
          {product?.truncatesProtein && truncationStartAa != null && (
            <div
              className="sv-pv-truncated-zone"
              style={{
                left: `${pct(truncationStartAa)}%`,
                width: `${Math.max(0, pct(referenceLen) - pct(truncationStartAa))}%`,
              }}
              title={`${product.lostAaCount} aa lost from variant-applied product`}
            />
          )}
          {signalPeptide && (
            <div
              className="sv-pv-region signal"
              style={spanStyle(signalPeptide.aaStart, signalPeptide.aaEnd)}
              title={`Signal peptide · aa ${signalPeptide.aaStart}–${signalPeptide.aaEnd}`}
            />
          )}
          {membraneBinding.map((r, i) => (
            <div
              key={`mb${i}`}
              className="sv-pv-region membrane"
              style={spanStyle(r.aaStart, r.aaEnd)}
              title={`${r.label} · aa ${r.aaStart}–${r.aaEnd}`}
            />
          ))}
          {domainBars.map((d, i) => {
            const left = pct(d.aaStart)
            const width = Math.max(0, pct(d.aaEnd) - left)
            const label = d.short || d.label
            return (
              <div
                key={`dom${i}`}
                className={`sv-pv-domain${d.broadBackbone ? ' family' : ''}`}
                style={{ left: `${left}%`, width: `${width}%` }}
                title={`${d.label} · aa ${d.aaStart}–${d.aaEnd}`}
              >
                {width > 14 ? label : ''}
              </div>
            )
          })}
          <span className="sv-pv-term n">N</span>
          <span className="sv-pv-term c">C</span>
          {product?.truncatesProtein && truncationStartAa != null && (
            <span
              className="sv-pv-stop"
              style={{ left: `${pct(truncationStartAa)}%` }}
              title={product.label}
            />
          )}
        </div>

        {/* Point features below the backbone */}
        <div className="sv-pv-points">
          {activeSites.map((a, i) => (
            <span
              key={`as${i}`}
              className="sv-pv-pt active"
              style={{ left: `${pct(a.aa)}%` }}
              title={`Active site · ${a.residue}${a.aa} · ${a.label}`}
            />
          ))}
          {palmitoylation.map((p, i) => (
            <span
              key={`pl${i}`}
              className="sv-pv-pt palmitoyl"
              style={{ left: `${pct(p.aa)}%` }}
              title={`${p.label} · ${p.residue}${p.aa}`}
            />
          ))}
        </div>

        <div className="sv-pv-scale">
          {scaleTicks.map((aa) => (
            <span key={aa} className="sv-pv-tick" style={{ left: `${pct(aa)}%` }}>
              {aa}
            </span>
          ))}
        </div>
      </div>

      <div className="sv-pv-legend">
        {product?.truncatesProtein && (
          <span className="sv-pv-product-note">{product.description}</span>
        )}
        <span>
          Lollipops are <b>uniform size</b> — ClinVar is a curated record set,
          not a cohort frequency table.
        </span>
        {splices.length > 0 && (
          <span className="sv-pv-splice-note">
            Splice/intronic (no protein coordinate):{' '}
            {splices.map((s) => `${s.hgvsC} (${classLabel(s.cls)})`).join(', ')}
          </span>
        )}
      </div>
    </div>
  )
})
