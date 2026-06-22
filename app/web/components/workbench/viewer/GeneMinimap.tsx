'use client'
import { memo, useMemo } from 'react'
import type { GeneWindowData } from '@/lib/workbench/gene-window'

interface GeneMinimapProps {
  data: GeneWindowData
  /** Currently-viewed exon (gets the active highlight + flag). */
  activeExon: number
  /** ClinVar density bubbles render only when true (driven by the unified
   *  ClinVar track toggle). */
  showDensity: boolean
  onExonClick: (exonNum: number) => void
}

type MinimapSegment =
  | {
      kind: 'utr5' | 'utr3'
      key: string
      num: number
      startPct: number
      widthPct: number
      bp: number
      units: number
    }
  | {
      kind: 'exon'
      key: string
      num: number
      startPct: number
      widthPct: number
      cdsStart: number
      cdsEnd: number
      bp: number
      units: number
      proteinState: GeneWindowData['exons'][number]['proteinState']
      lostCdsBases: number
    }
  | {
      kind: 'intron'
      key: string
      num: number
      startPct: number
      widthPct: number
      bp: number
      units: number
    }

type RawMinimapSegment = MinimapSegment extends infer Segment
  ? Segment extends unknown
    ? Omit<Segment, 'startPct' | 'widthPct'>
    : never
  : never

function compressedIntronUnits(bp: number): number {
  if (bp <= 0) return 0
  return Math.min(60, Math.max(8, Math.log10(bp + 1) * 12))
}

function clinvarShape(hgvsC: string, hgvsP: string, splice = false): 'missense' | 'truncating' | 'splice' {
  const text = `${hgvsC} ${hgvsP}`.toLowerCase()
  if (splice || text.includes('splice') || /c\.[^\s]*[+-][12](?:\D|$)/.test(text)) return 'splice'
  if (text.includes('ter') || text.includes('*') || text.includes('fs') || text.includes('frameshift') || text.includes('stop') || text.includes('trunc')) {
    return 'truncating'
  }
  return 'missense'
}

/** Whole-transcript band: proportional exon/intron segments, optional
 *  per-exon ClinVar density bubbles, active-window flag. Port of
 *  `sv-minimap.js`. */
export const GeneMinimap = memo(function GeneMinimap({
  data,
  activeExon,
  showDensity,
  onExonClick,
}: GeneMinimapProps) {
  const { segments, totalUnits, exonStarts } = useMemo(() => {
    const starts = new Map<number, number>()
    const raw: RawMinimapSegment[] = []
    if (data.utr5Length > 0) {
      raw.push({ kind: 'utr5', key: 'utr5', num: 0, bp: data.utr5Length, units: Math.max(18, Math.min(42, data.utr5Length)) })
    }
    data.exons.forEach((ex, idx) => {
      const exBp = ex.cdsEnd - ex.cdsStart + 1
      raw.push({
        kind: 'exon',
        key: `e${ex.num}`,
        num: ex.num,
        cdsStart: ex.cdsStart,
        cdsEnd: ex.cdsEnd,
        bp: exBp,
        units: Math.max(14, Math.min(80, exBp)),
        proteinState: ex.proteinState,
        lostCdsBases: ex.lostCdsBases ?? 0,
      })
      const intron = data.introns[idx]
      if (intron) {
        raw.push({
          kind: 'intron',
          key: `i${intron.num}`,
          num: intron.num,
          bp: intron.lenBp,
          units: compressedIntronUnits(intron.lenBp),
        })
      }
    })
    if (data.utr3Length > 0) {
      raw.push({ kind: 'utr3', key: 'utr3', num: 0, bp: data.utr3Length, units: Math.max(18, Math.min(42, data.utr3Length)) })
    }
    const total = raw.reduce((sum, seg) => sum + seg.units, 0)
    const pct = (units: number) => (total > 0 ? (units / total) * 100 : 0)
    let cursor = 0
    const segs = raw.map((seg): MinimapSegment => {
      if (seg.kind === 'exon') starts.set(seg.num, cursor)
      const positioned = {
        ...seg,
        startPct: pct(cursor),
        widthPct: pct(seg.units),
      } as MinimapSegment
      cursor += seg.units
      return positioned
    })
    return { segments: segs, totalUnits: total, exonStarts: starts }
  }, [data])

  const pctOfUnits = (units: number) => (totalUnits > 0 ? (units / totalUnits) * 100 : 0)

  const projectCds = (cds: number | string): number | null => {
    if (typeof cds !== 'number') return null
    const exon = segments.find(
      (seg): seg is Extract<MinimapSegment, { kind: 'exon' }> =>
        seg.kind === 'exon' && cds >= seg.cdsStart && cds <= seg.cdsEnd,
    )
    if (!exon) return null
    const span = Math.max(1, exon.cdsEnd - exon.cdsStart + 1)
    return exon.startPct + ((cds - exon.cdsStart) / span) * exon.widthPct
  }

  const queriedPct = projectCds(data.queriedVariant.cdsPos)
  const queriedShape = clinvarShape(data.queriedVariant.hgvsC, data.queriedVariant.hgvsP)
  const queriedLabel = data.queriedVariant.hgvsC
  const clinvarMarks = data.clinvar
    .map((variant) => {
      const pct = projectCds(variant.cdsPos)
      if (pct == null) return null
      return {
        pct,
        cls: variant.cls,
        label: variant.hgvsC || variant.hgvsP,
        shape: clinvarShape(variant.hgvsC, variant.hgvsP, Boolean(variant.splice)),
      }
    })
    .filter((mark): mark is NonNullable<typeof mark> => Boolean(mark))

  return (
    <div className="sv-minimap">
      <div className="sv-minimap-head">
        <span className="sv-minimap-title">Gene</span>
        <span className="sv-minimap-meta">
          {data.gene} · {data.geneLength.toLocaleString()} bp · {data.totalExons} exons
          · transcribed {data.nativeStrand === 'reverse' ? '←' : '→'} on {data.chrom}
        </span>
      </div>

      {showDensity && clinvarMarks.length > 0 && (
        <div className="sv-mm-clinvar" aria-label="ClinVar variants projected onto transcript">
          {clinvarMarks.map((mark, index) => (
            <span
              key={`${mark.label}-${index}`}
              className={`sv-mm-cv ${mark.cls} shape-${mark.shape}`}
              style={{ left: `${mark.pct}%` }}
              title={mark.label}
            />
          ))}
        </div>
      )}

      {showDensity && clinvarMarks.length === 0 && (
        <div className="sv-mm-bubbles">
          {data.exons.map((ex) => {
            const count = data.exonVariantCount[ex.num] || 0
            if (count === 0) return null
            const exBp = ex.cdsEnd - ex.cdsStart + 1
            const start = exonStarts.get(ex.num)
            if (start == null) return null
            const midPct = pctOfUnits(start + Math.max(14, Math.min(80, exBp)) / 2)
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
              className={[
                'sv-mm-seg',
                'exon',
                s.num === activeExon ? 'active' : '',
                s.proteinState === 'contains_variant' ? 'contains-variant' : '',
                s.proteinState === 'downstream_truncated' ? 'downstream-truncated' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              title={[
                `Exon ${s.num} · ${s.bp} bp · c.${s.cdsStart}–c.${s.cdsEnd}`,
                s.proteinState === 'contains_variant' ? 'variant-applied product starts here' : '',
                s.proteinState === 'downstream_truncated'
                  ? `${s.lostCdsBases} CDS bp lost from variant-applied product`
                  : '',
              ]
                .filter(Boolean)
                .join(' · ')}
              style={{ left: `${s.startPct}%`, width: `${s.widthPct}%` }}
              onClick={() => onExonClick(s.num)}
            >
              <span className={`sv-mm-exon-num${s.widthPct < 1.8 ? ' hidden' : ''}`}>
                {s.num}
              </span>
            </button>
          ) : (
            <div
              key={s.key}
              className={`sv-mm-seg ${s.kind}`}
              title={
                s.kind === 'intron'
                  ? `Intron ${s.num} · ${s.bp.toLocaleString()} bp`
                  : `${s.kind === 'utr5' ? "5'" : "3'"} UTR · ${s.bp.toLocaleString()} bp`
              }
              style={{ left: `${s.startPct}%`, width: `${s.widthPct}%` }}
            >
              {s.kind === 'utr5' ? "5'" : s.kind === 'utr3' ? "3'" : null}
            </div>
          ),
        )}
        {queriedPct != null && (
          <div
            className="sv-mm-query-pin"
            style={{ left: `${queriedPct}%` }}
            title={`${data.queriedVariant.hgvsC} · ${data.queriedVariant.hgvsP}`}
          >
            <span
              className={`sv-mm-query-head ${data.queriedVariant.classification} shape-${queriedShape}`}
              aria-hidden="true"
            />
            <span className="sv-mm-query-stem" aria-hidden="true" />
            <span className="sv-mm-query-label">{queriedLabel}</span>
          </div>
        )}
      </div>

      <div className="sv-mm-bookends">
        <span className="five">5′</span>
        <span className="bp">{data.cdsLength.toLocaleString()} bp CDS</span>
        <span className="three">3′</span>
      </div>
    </div>
  )
})
