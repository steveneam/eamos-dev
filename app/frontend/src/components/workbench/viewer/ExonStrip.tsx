import { classLabel, type GeneWindowData } from '@/lib/workbench/gene-window'

interface ExonStripProps {
  data: GeneWindowData
  activeExon: number
  onPinClick: (cdsPos: number) => void
}

/** Current-exon detail strip: header + ClinVar pins + a 5-tick ruler.
 *  Port of `renderExonStrip()`. */
export function ExonStrip({ data, activeExon, onPinClick }: ExonStripProps) {
  const ex = data.exons.find((e) => e.num === activeExon)
  if (!ex) return null
  const exLen = ex.cdsEnd - ex.cdsStart + 1
  const i3 = data.introns[ex.num - 2]
  const i4 = data.introns[ex.num - 1]

  return (
    <div className="sv-exonstrip">
      <div className="sv-exonstrip-head">
        <span className="sv-es-title">Exon {ex.num}</span>
        <span className="sv-es-meta">
          c.{ex.cdsStart}–c.{ex.cdsEnd} · {exLen} bp · codons{' '}
          {Math.ceil(ex.cdsStart / 3)}–{Math.ceil(ex.cdsEnd / 3)}
        </span>
        {i3 && i4 && (
          <span className="sv-es-meta dim">
            Flanked by intron {i3.num} ({i3.lenBp.toLocaleString()} bp) and intron{' '}
            {i4.num} ({i4.lenBp.toLocaleString()} bp)
          </span>
        )}
      </div>

      <div className="sv-exonstrip-bar">
        {data.clinvar.map((v) => {
          if (typeof v.cdsPos !== 'number') return null
          if (v.cdsPos < ex.cdsStart || v.cdsPos > ex.cdsEnd) return null
          const pct = ((v.cdsPos - ex.cdsStart) / exLen) * 100
          return (
            <button
              key={v.cv}
              type="button"
              className={`sv-es-pin ${v.cls}${v.queried ? ' queried' : ''}`}
              style={{ left: `${pct}%` }}
              title={`${v.hgvsC} · ${v.hgvsP} · ${classLabel(v.cls)}`}
              aria-label={`${v.hgvsC}, ${v.hgvsP}, ${classLabel(v.cls)}`}
              onClick={() => onPinClick(v.cdsPos as number)}
            />
          )
        })}
      </div>

      <div className="sv-es-ruler">
        {[0, 0.25, 0.5, 0.75, 1].map((p) => (
          <div key={p} className="sv-es-tick" style={{ left: `${p * 100}%` }}>
            <span>c.{Math.round(ex.cdsStart + p * (ex.cdsEnd - ex.cdsStart))}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
