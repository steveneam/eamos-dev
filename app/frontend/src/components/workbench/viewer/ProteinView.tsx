import { useMemo } from 'react'
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

export function ProteinView({ data, alleleMode }: ProteinViewProps) {
  const protLen = data.proteinLength || 1
  const pct = (aa: number) => ((aa - 1) / Math.max(1, protLen - 1)) * 100

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
  const queriedAa = qv.codonNumber

  return (
    <div className="sv-protein">
      <div className="sv-pv-head-row">
        <span className="sv-pv-title">Protein</span>
        <span className="sv-pv-meta">
          {data.gene} · {protLen} aa ·{' '}
          {alleleMode === 'variant' ? 'variant-applied' : 'reference'} ·{' '}
          {lollipops.length} ClinVar record{lollipops.length === 1 ? '' : 's'}{' '}
          projected
          {splices.length ? ` (+${splices.length} splice/intronic)` : ''}
        </span>
      </div>

      <div className="sv-pv-stage">
        {/* Lollipop track (above the backbone) */}
        <div className="sv-pv-lollipops">
          {lollipops.map((p) => {
            const h = 20 + p.lane * 16
            return (
              <div
                key={p.cv}
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
                  <span className="sv-pv-poplabel">
                    {p.hgvsC} · {p.hgvsP} (aa {p.aa})
                  </span>
                )}
              </div>
            )
          })}
        </div>

        {/* Backbone + domains + region features */}
        <div className="sv-pv-backbone">
          {signalPeptide && (
            <div
              className="sv-pv-region signal"
              style={{
                left: `${pct(signalPeptide.aaStart)}%`,
                width: `${pct(signalPeptide.aaEnd) - pct(signalPeptide.aaStart)}%`,
              }}
              title={`Signal peptide · aa ${signalPeptide.aaStart}–${signalPeptide.aaEnd}`}
            />
          )}
          {membraneBinding.map((r, i) => (
            <div
              key={`mb${i}`}
              className="sv-pv-region membrane"
              style={{
                left: `${pct(r.aaStart)}%`,
                width: `${pct(r.aaEnd) - pct(r.aaStart)}%`,
              }}
              title={`${r.label} · aa ${r.aaStart}–${r.aaEnd}`}
            />
          ))}
          {domainBars.map((d, i) => {
            const left = pct(d.aaStart)
            const width = pct(d.aaEnd) - left
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
          {[1, Math.round(protLen / 4), Math.round(protLen / 2), Math.round((3 * protLen) / 4), protLen].map(
            (aa, i) => (
              <span key={i} className="sv-pv-tick" style={{ left: `${pct(aa)}%` }}>
                {aa}
              </span>
            ),
          )}
        </div>
      </div>

      <div className="sv-pv-legend">
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
}
