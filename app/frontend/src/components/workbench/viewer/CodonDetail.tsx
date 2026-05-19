import {
  Fragment,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from 'react'
import { aaClass } from '@/lib/workbench/codon-table'
import {
  COMPLEMENT,
  classLabel,
  translateTriplet,
  type Codon,
  type FlatBase,
  type GeneWindowData,
} from '@/lib/workbench/gene-window'
import type { EditMap } from '@/lib/workbench/edit-state'
import { buildLayout, MIN_BP, type LayoutItem } from '@/lib/workbench/codon-layout'
import type { AlleleMode } from '@/lib/backend'
import type { StrandMode, TrackState } from './viewer-types'

const RIGHT_MARGIN = 64
/** Sub-pixel cushion so the widest row never forces a horizontal scrollbar. */
const REFLOW_PAD = 2

interface CodonDetailProps {
  data: GeneWindowData
  flat: FlatBase[]
  codons: Codon[]
  baseW: number
  trackOn: TrackState
  strandMode: StrandMode
  /** Reference/control vs variant-applied. The adapter already applied the
   *  SNV to `data` in `variant` mode; the queried codon then shows its
   *  ref→alt AA change (the old FE-5.6 always-on synthetic baseline is
   *  superseded — the displayed allele is now adapter-driven, GV-006). */
  alleleMode: AlleleMode
  edits: EditMap
  selection: { start: number; end: number } | null
  searchQuery: string
  restrictionHover: string | null
  onBaseMouseDown: (idx: number, shiftKey: boolean) => void
  onBaseContextMenu: (idx: number, x: number, y: number) => void
  onClinvarClick: (idx: number) => void
  onRestrictionHover: (name: string | null) => void
  onRestrictionSelect: (start: number, end: number) => void
}

export function CodonDetail(props: CodonDetailProps) {
  const { flat, baseW } = props
  const detailRef = useRef<HTMLDivElement>(null)
  const [containerW, setContainerW] = useState(0)

  // Live container width → bases-per-row. The ResizeObserver covers
  // side-panel collapse (the content box widens with no zoom change); the
  // rowBp memo also keys off baseW so zoom reflows even though zoom does not
  // change the container width. Observer is disconnected on unmount.
  useLayoutEffect(() => {
    const el = detailRef.current
    if (!el) return
    const measure = () => {
      const cs = getComputedStyle(el)
      setContainerW(
        el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
      )
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const rowBp = useMemo(
    () => Math.max(MIN_BP, Math.floor((containerW - RIGHT_MARGIN - REFLOW_PAD) / baseW)),
    [containerW, baseW],
  )
  const layout = useMemo<LayoutItem[]>(() => buildLayout(flat, rowBp), [flat, rowBp])

  // GV-006: the displayed allele basis is now adapter-driven — in `variant`
  // mode the queried SNV is already applied to `data` (and thus `flat`), so
  // the translation follows the sequence honestly per mode. The FE-5.6
  // always-on synthetic baseline overlay is superseded; the queried codon's
  // ref→alt badge is reconstructed from `data.queriedVariant` in
  // `Block.translation()` so it survives the variant-applied `flat`.

  const baseFlatIndex = useMemo(() => {
    const m = new Map<number, number>()
    let n = 0
    flat.forEach((b) => {
      if (b.kind !== 'intron-gap') m.set(b.flatPos, n++)
    })
    return m
  }, [flat])

  return (
    <div className="sv-detail" ref={detailRef}>
      {layout.map((item, k) =>
        item.kind === 'gap' ? (
          <div className="sv-gap-sep" key={`gap${k}`}>
            <span className="ic">···</span>
            <span className="msg">
              <b>{item.omitted.toLocaleString()} bp</b> of intron {item.intronNum} omitted
            </span>
            <span className="ic">···</span>
          </div>
        ) : (
          <Block
            key={`row${item.indices[0]}`}
            indices={item.indices}
            baseFlatIndex={baseFlatIndex}
            {...props}
          />
        ),
      )}
    </div>
  )
}

interface BlockProps extends CodonDetailProps {
  indices: number[]
  baseFlatIndex: Map<number, number>
}

function Block(props: BlockProps) {
  const {
    data,
    flat,
    codons,
    baseW,
    trackOn,
    strandMode,
    alleleMode,
    edits,
    selection,
    searchQuery,
    restrictionHover,
    indices,
    baseFlatIndex,
    onBaseMouseDown,
    onBaseContextMenu,
    onClinvarClick,
    onRestrictionHover,
    onRestrictionSelect,
  } = props

  const w = indices.length * baseW
  const startIdx = indices[0]
  const endIdx = indices[indices.length - 1]
  const posOf = (i: number) => indices.indexOf(i)
  const localX = (i: number) => posOf(i) * baseW

  // ── Annotation row: exon/intron feature bars + splice tags + oligo ──
  function annotations() {
    const groups: Array<{
      kind: string
      exonNum?: number
      intronNum?: number
      start: number
      end: number
    }> = []
    let cur: (typeof groups)[number] | null = null
    indices.forEach((i) => {
      const b = flat[i]
      const key =
        b.kind === 'exon' ? `e${b.exonNum}` : b.kind === 'intron' ? `i${b.intronNum}` : 'x'
      if (!cur || (cur.kind === 'exon' ? `e${cur.exonNum}` : `i${cur.intronNum}`) !== key) {
        cur = {
          kind: b.kind,
          exonNum: b.kind === 'exon' ? b.exonNum : undefined,
          intronNum: b.kind === 'intron' ? b.intronNum : undefined,
          start: i,
          end: i,
        }
        groups.push(cur)
      } else cur.end = i
    })

    const bars = groups.map((g, gi) => {
      const left = localX(g.start)
      const width = localX(g.end) + baseW - left
      if (g.kind === 'exon') {
        const ex = data.exons.find((e) => e.num === g.exonNum)
        return (
          <div
            key={`g${gi}`}
            className="sv-feat-bar exon"
            style={{ left, width }}
          >
            Exon {g.exonNum}
            {ex ? ` · c.${ex.cdsStart}–${ex.cdsEnd}` : ''}
          </div>
        )
      }
      return (
        <div key={`g${gi}`} className="sv-feat-bar intron" style={{ left, width }}>
          Intron {g.intronNum} ({data.introns[(g.intronNum ?? 1) - 1].lenBp.toLocaleString()} bp)
        </div>
      )
    })

    const spliceTags = indices
      .map((i) => {
        const b = flat[i]
        if (b.kind !== 'intron' || !b.isSplice) return null
        const isFirst =
          (b.intronEnd === '5prime' && b.intronOffset === 1) ||
          (b.intronEnd === '3prime' && b.intronOffset === -2)
        if (!isFirst) return null
        const donor = b.intronEnd === '5prime'
        return (
          <div
            key={`sp${i}`}
            className={`sv-splice-tag ${donor ? 'donor' : 'acceptor'}`}
            style={{ left: localX(i), width: baseW * 2 }}
          >
            {donor ? 'GT · 5′ SS' : 'AG · 3′ SS'}
          </div>
        )
      })
      .filter(Boolean)

    const oligos = data.features
      .filter((f) => f.type === 'oligo')
      .map((f, oi) => {
        const fStart = flat.findIndex((b) => b.kind === 'exon' && b.cdsPos === f.cdsStart)
        const fEnd = flat.findIndex((b) => b.kind === 'exon' && b.cdsPos === f.cdsEnd)
        if (fStart < 0 || fEnd < 0) return null
        const oStart = Math.max(fStart, startIdx)
        const oEnd = Math.min(fEnd, endIdx)
        if (oEnd < oStart) return null
        const left = localX(oStart)
        const width = localX(oEnd) + baseW - left
        return (
          <div
            key={`ol${oi}`}
            className="sv-feat-bar oligo"
            style={{ left, width, top: 0, height: 8, transform: 'none' }}
            title={f.label}
          >
            {width > 80 ? f.label : ''}
          </div>
        )
      })
      .filter(Boolean)

    return [...bars, ...spliceTags, ...oligos]
  }

  // ── ClinVar dots ──
  function clinvar() {
    const intronicIndex = (cdsPos: string) => {
      const m = /^(\d+)([+-])(\d+)$/.exec(cdsPos)
      if (!m) return -1
      const exonEdge = parseInt(m[1], 10)
      const sign = m[2]
      const off = parseInt(m[3], 10) * (sign === '+' ? 1 : -1)
      const exon =
        sign === '+'
          ? data.exons.find((e) => e.cdsEnd === exonEdge)
          : data.exons.find((e) => e.cdsStart === exonEdge)
      if (!exon) return -1
      const intronNum = sign === '+' ? exon.num : exon.num - 1
      return flat.findIndex(
        (b) => b.kind === 'intron' && b.intronNum === intronNum && b.intronOffset === off,
      )
    }

    return data.clinvar.map((v) => {
      let idx = -1
      if (typeof v.cdsPos === 'number') {
        idx = flat.findIndex((b) => b.kind === 'exon' && b.cdsPos === v.cdsPos)
      } else if (v.splice) {
        idx = intronicIndex(v.cdsPos)
      }
      if (idx < 0 || !indices.includes(idx)) return null
      return (
        <button
          key={v.cv}
          type="button"
          className={`sv-cv ${v.cls}${v.queried ? ' queried' : ''}`}
          style={{ left: localX(idx) + baseW / 2 }}
          title={`${v.hgvsC} · ${v.hgvsP} · ${classLabel(v.cls)}`}
          aria-label={`${v.hgvsC}, ${v.hgvsP}, ${classLabel(v.cls)}`}
          onClick={(e) => {
            e.stopPropagation()
            onClinvarClick(idx)
          }}
        />
      )
    })
  }

  // ── Translation (codons → AA pills) ──
  function translation() {
    return codons.map((c) => {
      const inRow = c.bases.filter((i) => indices.includes(i))
      if (inRow.length === 0) return null
      const allHere = inRow.length === 3
      const left = allHere ? localX(c.bases[0]) : localX(inRow[0])
      const width = allHere
        ? 3 * baseW
        : localX(inRow[inRow.length - 1]) + baseW - left
      const refTriplet = c.bases.map((i) => flat[i].base).join('').toUpperCase()
      const editTriplet = c.bases
        .map((i) => {
          const e = edits.get(i)
          if (!e) return flat[i].base
          if (e.kind === 'sub') return e.alt
          if (e.kind === 'del') return '-'
          return flat[i].base
        })
        .join('')
        .toUpperCase()
      const refAA = translateTriplet(refTriplet)
      const editAA = editTriplet.includes('-') ? '-' : translateTriplet(editTriplet)
      const queried = c.codonNum === data.queriedVariant.codonNumber

      // In `variant` mode the SNV is already applied to `flat` (adapter), so
      // refTriplet == editTriplet for the queried codon. Reconstruct the
      // ref→alt badge from the authoritative queried-variant metadata so the
      // change still reads (e.g. Asp→Gly). A user edit on that codon takes
      // precedence and falls through to the normal edit-derived display.
      const userEditedCodon = c.bases.some((i) => edits.has(i))
      const useQv = queried && alleleMode === 'variant' && !userEditedCodon
      const dRefAA = useQv ? data.queriedVariant.aaRef || refAA : refAA
      const dEditAA = useQv ? data.queriedVariant.aaAlt || editAA : editAA
      const changed = dEditAA !== dRefAA
      const insAnywhere = c.bases.some((i) => edits.get(i)?.kind === 'ins')
      const cls = [
        'sv-codon',
        queried ? 'queried' : '',
        changed ? 'changed' : '',
        c.spansSplice ? 'spans-splice' : '',
        insAnywhere ? 'frameshift' : '',
        !allHere ? 'partial' : '',
      ]
        .filter(Boolean)
        .join(' ')
      const showNum =
        c.codonNum % 5 === 0 || c.codonNum === data.queriedVariant.codonNumber
      return (
        <div key={`c${c.codonNum}`} className={cls} style={{ left, width }}>
          <div className={`sv-aa ${aaClass[dEditAA] || 'hydro'}`}>
            {editTriplet.includes('-') ? '•' : dEditAA}
            {changed && allHere && <span className="sv-aa-old">{dRefAA}</span>}
          </div>
          {showNum && allHere && <div className="sv-aa-num">{c.codonNum}</div>}
        </div>
      )
    })
  }

  // ── Ruler ──
  function ruler() {
    return indices.map((i) => {
      const b = flat[i]
      if (b.kind !== 'exon' || b.cdsPos % 10 !== 0) return null
      return (
        <div
          key={`r${i}`}
          className="sv-ruler-tick"
          style={{ left: localX(i) + baseW / 2 }}
        >
          c.{b.cdsPos}
        </div>
      )
    })
  }

  // ── Bases (one strand) ──
  function searchHit(i: number): boolean {
    const q = searchQuery.trim().toUpperCase()
    if (!/^[ATCG]{3,}$/.test(q)) return false
    const s = flat.map((b) => (b.kind === 'intron-gap' ? '_' : b.base.toUpperCase())).join('')
    let pos = -1
    while ((pos = s.indexOf(q, pos + 1)) >= 0) {
      if (i >= pos && i < pos + q.length) return true
    }
    return false
  }
  function restrictionHit(i: number): boolean {
    if (!restrictionHover) return false
    const re = data.restriction.find((r) => r.name === restrictionHover)
    if (!re) return false
    return i >= re.flatPos && i < re.flatPos + re.site.length
  }

  function bases(which: 'top' | 'complement') {
    const isComp = which === 'complement'
    const isRev = strandMode === 'rev'
    const qIdx = flat.findIndex(
      (b) => b.kind === 'exon' && b.cdsPos === data.queriedVariant.cdsPos,
    )
    const cells = indices.map((i) => {
      const b = flat[i]
      const left = posOf(i) * baseW
      const edit = !isComp ? edits.get(i) : undefined
      let display = b.base
      const cls = ['sv-base']
      if (!edit) cls.push(b.base.toUpperCase())
      if (isComp) cls.push('complement')
      if (edit?.kind === 'sub') {
        display = edit.alt
        cls.push(display.toUpperCase(), 'edited')
      } else if (edit?.kind === 'del') {
        display = '–'
        cls.push('edited', 'del')
      } else if (edit?.kind === 'ins') {
        cls.push('edited', 'ins')
      }
      if (b.kind === 'intron') {
        cls.push('intron')
        if (b.isSplice) cls.push('splice')
      }
      if (
        b.kind === 'exon' &&
        b.cdsPos === data.queriedVariant.cdsPos &&
        !isComp &&
        !edit
      ) {
        cls.push('variant')
      }
      if (isComp) display = COMPLEMENT[display] || display
      if (isRev && !isComp) display = COMPLEMENT[display] || display
      const text =
        b.kind === 'intron' ? display.toLowerCase() : display.toUpperCase()
      if (
        !isComp &&
        selection &&
        i >= Math.min(selection.start, selection.end) &&
        i <= Math.max(selection.start, selection.end)
      ) {
        cls.push('selected')
      }
      if (searchHit(i)) cls.push('search-hit')
      if (restrictionHit(i)) cls.push('restriction-hit')
      const title =
        b.kind === 'exon'
          ? `c.${b.cdsPos} · ref ${b.base.toUpperCase()}${edit ? ' → edited' : ''}`
          : b.kind === 'intron'
            ? `intron ${b.intronNum} ${b.intronOffset > 0 ? '+' : ''}${b.intronOffset}${
                b.isSplice
                  ? ` (splice ${b.intronEnd === '5prime' ? 'donor GT' : 'acceptor AG'})`
                  : ''
              }`
            : ''
      return (
        <Fragment key={`b${which}${i}`}>
          <div
            className={cls.join(' ')}
            style={{ left, width: baseW }}
            data-idx={isComp ? undefined : i}
            title={title}
            onMouseDown={
              isComp
                ? undefined
                : (e) => {
                    if (e.button === 0) onBaseMouseDown(i, e.shiftKey)
                  }
            }
            onContextMenu={
              isComp
                ? undefined
                : (e) => {
                    e.preventDefault()
                    onBaseContextMenu(i, e.clientX, e.clientY)
                  }
            }
          >
            {text}
          </div>
          {!isComp && edit?.kind === 'ins' && (
            <div
              className="sv-ins-marker"
              style={{ left: left + baseW }}
              title={`Insertion of ${edit.alt} after this base`}
            >
              +{edit.alt.length}
            </div>
          )}
        </Fragment>
      )
    })
    const marker =
      !isComp && qIdx >= 0 && indices.includes(qIdx) ? (
        <div
          className="sv-marker-thin"
          style={{ left: posOf(qIdx) * baseW + baseW / 2 }}
        />
      ) : null
    return (
      <>
        {cells}
        {marker}
      </>
    )
  }

  function rightPos(which: 'top' | 'complement') {
    const last = flat[endIdx]
    if (which === 'complement') {
      return (
        <div className="sv-block-pos">
          <span className="sub">{strandMode === 'rev' ? '5′' : '3′'} ←</span>
        </div>
      )
    }
    const label =
      last.kind === 'exon'
        ? `c.${last.cdsPos}`
        : last.kind === 'intron'
          ? `i${last.intronNum} ${last.intronOffset > 0 ? '+' : ''}${last.intronOffset}`
          : ''
    return (
      <div className="sv-block-pos">
        <span>{label}</span>
        <span className="sub">{strandMode === 'rev' ? '3′' : '5′'} →</span>
      </div>
    )
  }

  // ── Conservation ──
  function conservation() {
    return indices.map((i) => {
      const v = data.conservation[baseFlatIndex.get(i) ?? -1] || 0
      return (
        <div
          key={`cs${i}`}
          className={`sv-cons-bar${flat[i].kind === 'intron' ? ' intronic' : ''}`}
          style={{ left: posOf(i) * baseW + baseW / 2, height: v * 26 }}
          title={`PhyloP ${v.toFixed(2)}`}
        />
      )
    })
  }

  // ── Restriction (top-edge bars) ──
  function restriction() {
    return data.restriction.map((re) => {
      const span = [re.flatPos, re.flatPos + re.site.length - 1]
      const inRow = indices.filter((i) => i >= span[0] && i <= span[1])
      if (inRow.length === 0) return null
      const left = localX(inRow[0])
      const width = localX(inRow[inRow.length - 1]) + baseW - left
      return (
        <div
          key={re.name}
          className="sv-re-bar"
          style={{ left, width }}
          title={`${re.name} · ${re.site} · ${re.site.length} bp`}
          role="button"
          tabIndex={0}
          aria-label={`Select ${re.name} restriction site, ${re.site}, ${re.site.length} bp`}
          onMouseEnter={() => onRestrictionHover(re.name)}
          onMouseLeave={() => onRestrictionHover(null)}
          onClick={() => onRestrictionSelect(re.flatPos, re.flatPos + re.site.length - 1)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onRestrictionSelect(re.flatPos, re.flatPos + re.site.length - 1)
            }
          }}
        >
          {re.name} {re.site}
        </div>
      )
    })
  }

  const row = (cls: string, height: number, children: React.ReactNode) => (
    <div className={`sv-block-row ${cls}`} style={{ height, width: w }}>
      {children}
    </div>
  )
  const blockStyle: CSSProperties = { width: w + RIGHT_MARGIN }

  return (
    <div className="sv-block" style={blockStyle}>
      {trackOn.annotations && row('annotations', 22, annotations())}
      {trackOn.domains &&
        row(
          'domain',
          18,
          <div className="sv-feat-bar domain" style={{ left: 0, width: w }}>
            {data.domains[0].shortLabel} (aa {data.domains[0].aaStart}–{data.domains[0].aaEnd})
          </div>,
        )}
      {trackOn.clinvar && row('clinvar', 12, clinvar())}
      {row('translation', 28, translation())}
      {row('ruler', 14, ruler())}
      <div className="sv-block-row sequence" style={{ height: 24, width: w }}>
        {bases('top')}
        {rightPos('top')}
      </div>
      {strandMode === 'both' && (
        <div className="sv-block-row sequence complement" style={{ height: 22, width: w }}>
          {bases('complement')}
          {rightPos('complement')}
        </div>
      )}
      {trackOn.conservation && row('conservation', 30, conservation())}
      {trackOn.restriction && row('restriction', 22, restriction())}
    </div>
  )
}
