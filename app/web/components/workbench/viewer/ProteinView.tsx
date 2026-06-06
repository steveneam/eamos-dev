'use client'
import { memo, useMemo } from 'react'
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
  queried: boolean
  hgvsC: string
  hgvsP: string
  cv: string
}

/** Consecutive variants closer than this (in % of the backbone) are stacked
 *  into higher lanes so heads + stems do not overlap. Heuristic — the view
 *  is responsive and cannot measure px without an observer. */
const LANE_GAP_PCT = 3.4
const MAX_LANES = 4

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

  const { lollipops, splices } = useMemo(() => {
    const splices: GeneWindowData['clinvar'] = []
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
      .sort((a, b) => a.aa - b.aa)

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
        queried: Boolean(v.queried),
        hgvsC: v.hgvsC,
        hgvsP: v.hgvsP,
        cv: v.cv,
      }
    })
    return { lollipops: pops, splices }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, protLen])

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
  }))
  const { activeSites, membraneBinding, palmitoylation, signalPeptide } =
    data.proteinFeatures

  const qv = data.queriedVariant
  const queriedAa = qv.codonNumber || Math.ceil(qv.cdsPos / 3) || 1

  return (
    <div className="sv-protein">
      <div className="sv-pv-head-row">
        <span className="sv-pv-title">Protein</span>
        <span className="sv-pv-meta">
          {data.gene} ·{' '}
          {product?.truncatesProtein
            ? `${effectiveLen} / ${referenceLen} aa`
            : `${protLen} aa`}{' '}
          ·{' '}
          {alleleMode === 'variant' ? 'variant-applied' : 'reference'} ·{' '}
          {product?.truncatesProtein ? `${product.label} · ` : ''}
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
                style={{ left: `${p.xPct}%`, height: h }}
                title={`${p.hgvsC} · ${p.hgvsP} · ${classLabel(p.cls)}${
                  p.queried ? ' · queried' : ''
                }`}
              >
                <span className="sv-pv-stem" style={{ height: h }} />
                <span
                  className={`sv-pv-headdot ${p.cls}${
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
                className="sv-pv-domain"
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
          <span
            className="sv-pv-pt query"
            style={{ left: `${pct(queriedAa)}%` }}
            title={`Queried · ${qv.hgvsC} · ${qv.hgvsP}`}
          />
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
