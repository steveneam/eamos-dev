import { useMemo } from 'react'
import type { GeneWindowData } from '@/lib/workbench/gene-window'

interface GeneMinimapProps {
  data: GeneWindowData
  /** Currently-viewed exon (gets the active highlight + flag). */
  activeExon: number
  /** Modification #1: ClinVar density bubbles render only when true. */
  showDensity: boolean
  onExonClick: (exonNum: number) => void
}

/** Whole-transcript band: proportional exon/intron segments, optional
 *  per-exon ClinVar density bubbles, active-window flag. Port of
 *  `sv-minimap.js`. */
export function GeneMinimap({
  data,
  activeExon,
  showDensity,
  onExonClick,
}: GeneMinimapProps) {
  const { segments, totalBp } = useMemo(() => {
    const total =
      data.exons.reduce((s, e) => s + (e.cdsEnd - e.cdsStart + 1), 0) +
      data.introns.reduce((s, i) => s + i.lenBp, 0)
    const segs: Array<
      | { kind: 'exon'; num: number; startPct: number; widthPct: number; cdsStart: number; cdsEnd: number; bp: number }
      | { kind: 'intron'; num: number; startPct: number; widthPct: number; bp: number }
    > = []
    let cursor = 0
    data.exons.forEach((ex, idx) => {
      const exBp = ex.cdsEnd - ex.cdsStart + 1
      segs.push({
        kind: 'exon',
        num: ex.num,
        startPct: (cursor / total) * 100,
        widthPct: (exBp / total) * 100,
        cdsStart: ex.cdsStart,
        cdsEnd: ex.cdsEnd,
        bp: exBp,
      })
      cursor += exBp
      if (idx < data.introns.length) {
        const inLen = data.introns[idx].lenBp
        segs.push({
          kind: 'intron',
          num: data.introns[idx].num,
          startPct: (cursor / total) * 100,
          widthPct: (inLen / total) * 100,
          bp: inLen,
        })
        cursor += inLen
      }
    })
    return { segments: segs, totalBp: total }
  }, [data])

  const segStartBp = (exonNum: number) =>
    data.exons.slice(0, exonNum - 1).reduce((s, e) => s + (e.cdsEnd - e.cdsStart + 1), 0) +
    data.introns.slice(0, exonNum - 1).reduce((s, i) => s + i.lenBp, 0)

  const activeMidPct = useMemo(() => {
    const ex = data.exons.find((e) => e.num === activeExon)
    if (!ex) return 0
    return ((segStartBp(activeExon) + (ex.cdsEnd - ex.cdsStart + 1) / 2) / totalBp) * 100
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, activeExon, totalBp])

  return (
    <div className="sv-minimap">
      <div className="sv-minimap-head">
        <span className="sv-minimap-title">Gene</span>
        <span className="sv-minimap-meta">
          {data.gene} · {data.geneLength.toLocaleString()} bp · {data.totalExons} exons
          · transcribed {data.nativeStrand === 'reverse' ? '←' : '→'} on {data.chrom}
        </span>
      </div>

      {showDensity && (
        <div className="sv-mm-bubbles">
          {data.exons.map((ex) => {
            const count = data.exonVariantCount[ex.num] || 0
            if (count === 0) return null
            const exBp = ex.cdsEnd - ex.cdsStart + 1
            const midPct = ((segStartBp(ex.num) + exBp / 2) / totalBp) * 100
            const r = Math.min(11, 3 + Math.sqrt(count) * 1.2)
            return (
              <div
                key={ex.num}
                className="sv-mm-bubble"
                title={`Exon ${ex.num} · ${count} ClinVar variants`}
                style={{
                  left: `${midPct}%`,
                  width: r,
                  height: r,
                  marginLeft: -r / 2,
                }}
              />
            )
          })}
        </div>
      )}

      <div className="sv-minimap-band">
        {segments.map((s) =>
          s.kind === 'exon' ? (
            <button
              key={`e${s.num}`}
              type="button"
              className={`sv-mm-seg exon${s.num === activeExon ? ' active' : ''}`}
              title={`Exon ${s.num} · ${s.bp} bp · c.${s.cdsStart}–c.${s.cdsEnd}`}
              style={{ left: `${s.startPct}%`, width: `${s.widthPct}%` }}
              onClick={() => onExonClick(s.num)}
            >
              <span className={`sv-mm-exon-num${s.widthPct < 1.8 ? ' hidden' : ''}`}>
                {s.num}
              </span>
            </button>
          ) : (
            <div
              key={`i${s.num}`}
              className="sv-mm-seg intron"
              title={`Intron ${s.num} · ${s.bp.toLocaleString()} bp`}
              style={{ left: `${s.startPct}%`, width: `${s.widthPct}%` }}
            />
          ),
        )}
      </div>

      <div className="sv-mm-flag" style={{ left: `${activeMidPct}%` }}>
        <span>{data.queriedVariant.hgvsC.replace(/^c\./, 'c.')}</span>
      </div>

      <div className="sv-mm-bookends">
        <span className="five">5′</span>
        <span className="bp">{data.cdsLength.toLocaleString()} bp CDS</span>
        <span className="three">3′</span>
      </div>
    </div>
  )
}
