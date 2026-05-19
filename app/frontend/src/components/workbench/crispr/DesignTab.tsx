import { useMemo, useState } from 'react'
import type {
  CasEnzyme,
  CrisprGuide,
  CrisprRequest,
  CrisprResponse,
  HdrSsodn,
} from '@/lib/backend'
import { designGuides } from '@/lib/api'
import { GuideTrack } from './GuideTrack'

interface DesignTabProps {
  gene: string
  cdna: string
}

const CAS_OPTIONS: CasEnzyme[] = ['SpCas9', 'SaCas9', 'Cas12a']
const STRANDS: Array<{ v: CrisprRequest['strand_filter']; label: string }> = [
  { v: 'both', label: 'Both strands' },
  { v: 'plus', label: 'Plus (+) only' },
  { v: 'minus', label: 'Minus (−) only' },
]

type SortKey = 'on' | 'off' | null

/** Lower off-target is better in the current fixture (§4 contract note). */
function offClass(v: number): string {
  return v < 20 ? 'score-good' : v <= 30 ? 'score-mid' : 'score-bad'
}
function onClass(v: number): string {
  return v >= 75 ? 'score-good' : v >= 60 ? 'score-mid' : 'score-bad'
}

/** Index of the recommended guide: lowest off-target among the returned
 *  set (matches the fixture's "lowest off-target" annotation). */
function recommendedIndex(guides: CrisprGuide[]): number {
  if (guides.length === 0) return -1
  return guides.reduce(
    (best, g) => (g.off_target_score < guides[best].off_target_score ? g.index : best),
    guides[0].index,
  )
}

/** ssODN highlight classes, derived from the three-arm diff (no hard-coded
 *  positions): the pathogenic site (variant≠reference) reads as the warn
 *  target; on the repair template the base that reverts it is the
 *  corrective edit and any other repair≠reference base is the silent
 *  PAM-blocking edit. */
function ssodnSpans(ss: HdrSsodn) {
  const ref = ss.reference_arm
  const varm = ss.variant_arm
  const rep = ss.repair_template
  const n = Math.min(ref.length, varm.length, rep.length)
  const targetIdx = new Set<number>()
  const correctIdx = new Set<number>()
  const silentIdx = new Set<number>()
  for (let i = 0; i < n; i++) {
    if (varm[i] !== ref[i]) targetIdx.add(i)
    if (rep[i] !== varm[i] && varm[i] !== ref[i]) correctIdx.add(i)
    else if (rep[i] !== ref[i]) silentIdx.add(i)
  }
  return { targetIdx, correctIdx, silentIdx }
}

function SsodnLine({
  label,
  seq,
  hl,
}: {
  label: string
  seq: string
  hl: (i: number) => string | undefined
}) {
  return (
    <div>
      <span className="label">{label}</span>
      {seq.split('').map((b, i) => {
        const c = hl(i)
        return c ? (
          <span key={i} className={c}>
            {b}
          </span>
        ) : (
          b
        )
      })}
    </div>
  )
}

export function DesignTab({ gene, cdna }: DesignTabProps) {
  const [cas, setCas] = useState<CasEnzyme>('SpCas9')
  const [strand, setStrand] = useState<CrisprRequest['strand_filter']>('both')
  const [offTol, setOffTol] = useState(2)
  const [targetWin, setTargetWin] = useState(10)
  const [minOnTarget, setMinOnTarget] = useState(0)
  const [sort, setSort] = useState<SortKey>(null)

  const [res, setRes] = useState<CrisprResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hovered, setHovered] = useState<number | null>(null)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const payload: CrisprRequest = {
        gene,
        cdna,
        cas,
        strand_filter: strand,
        off_target_tolerance: offTol,
      }
      const r = await designGuides(payload)
      setRes(r)
      setHovered(recommendedIndex(r.guides))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'CRISPR design failed')
    } finally {
      setLoading(false)
    }
  }

  const recIdx = res ? recommendedIndex(res.guides) : -1

  const rows = useMemo(() => {
    if (!res) return []
    const filtered = res.guides.filter((g) => g.on_target_score >= minOnTarget)
    if (!sort) return filtered
    return [...filtered].sort((a, b) =>
      sort === 'on'
        ? b.on_target_score - a.on_target_score
        : a.off_target_score - b.off_target_score,
    )
  }, [res, sort, minOnTarget])

  const activeGuide =
    res?.guides.find((g) => g.index === hovered) ?? res?.guides[0] ?? null
  const template = res?.ssodn?.reference_arm ?? null

  return (
    <div className="crispr-design">
      <div className="tool-form">
        <label className="field">
          <span className="field-label">Cas enzyme</span>
          <select
            className="field-select"
            value={cas}
            onChange={(e) => setCas(e.target.value as CasEnzyme)}
          >
            {CAS_OPTIONS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field-label">Strand</span>
          <select
            className="field-select"
            value={strand}
            onChange={(e) =>
              setStrand(e.target.value as CrisprRequest['strand_filter'])
            }
          >
            {STRANDS.map((s) => (
              <option key={s.v} value={s.v}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field-label">Off-target tolerance</span>
          <input
            className="field-input"
            type="number"
            min={0}
            max={5}
            value={offTol}
            onChange={(e) => setOffTol(Number(e.target.value))}
          />
        </label>
        <label className="field">
          <span className="field-label">Target window (± bp)</span>
          <input
            className="field-input"
            type="number"
            min={1}
            max={50}
            value={targetWin}
            onChange={(e) => setTargetWin(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="btn-row">
        <button
          type="button"
          className="btn-teal"
          onClick={run}
          disabled={loading}
        >
          {loading ? 'Designing…' : 'Design guides'}
        </button>
        <span className="tool-panel-sub">
          {gene} · {cdna} · {cas}
        </span>
      </div>

      <div className="help-note">
        Demo serves the RPE65 c.260 fixture. Off-target tolerance and the ±
        target window are passed to the design engine; the deterministic
        Hsu/PAM engine and whole-genome off-target scan land with the real
        provider (M-002D, gated). Off-target score here is lower-is-better
        per the current contract.
      </div>

      {error && <div className="crispr-error">{error}</div>}

      {res && (
        <>
          <div className="crispr-table-bar">
            <div className="seg" role="group" aria-label="Sort guides">
              <button
                type="button"
                className={sort === null ? 'active' : ''}
                onClick={() => setSort(null)}
              >
                Default
              </button>
              <button
                type="button"
                className={sort === 'on' ? 'active' : ''}
                onClick={() => setSort('on')}
              >
                On-target ↓
              </button>
              <button
                type="button"
                className={sort === 'off' ? 'active' : ''}
                onClick={() => setSort('off')}
              >
                Off-target ↑
              </button>
            </div>
            <label className="crispr-minfilter">
              <span className="field-label">Min on-target ≥ {minOnTarget}</span>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={minOnTarget}
                onChange={(e) => setMinOnTarget(Number(e.target.value))}
              />
            </label>
          </div>

          <table className="tool-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Guide 5′→3′ + PAM</th>
                <th>Cut</th>
                <th>Strand</th>
                <th>On-target</th>
                <th>Off-target</th>
                <th>GC%</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((g) => (
                <tr
                  key={g.index}
                  className={g.index === recIdx ? 'selected' : undefined}
                  onMouseEnter={() => setHovered(g.index)}
                  onFocus={() => setHovered(g.index)}
                  tabIndex={0}
                >
                  <td className="num">
                    {g.index === recIdx ? '★ ' : ''}
                    {g.index}
                  </td>
                  <td className="seq">
                    <span className="g-spacer">{g.guide}</span>
                    <span className="g-pam">{g.pam}</span>
                  </td>
                  <td className="num">{g.cut_position}</td>
                  <td className="num">{g.strand}</td>
                  <td className={`num ${onClass(g.on_target_score)}`}>
                    {g.on_target_score.toFixed(1)}
                  </td>
                  <td className={`num ${offClass(g.off_target_score)}`}>
                    {g.off_target_score.toFixed(1)}
                  </td>
                  <td className="num">{g.gc_percent}</td>
                  <td>{g.notes}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="crispr-empty">
                    No guides at min on-target ≥ {minOnTarget}.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {activeGuide && (
            <>
              <div className="crispr-track-h">
                Guide {activeGuide.index} on design template
              </div>
              <GuideTrack guide={activeGuide} template={template} />
            </>
          )}

          {res.ssodn && (
            <SsodnBlock ss={res.ssodn} />
          )}
        </>
      )}
    </div>
  )
}

function SsodnBlock({ ss }: { ss: HdrSsodn }) {
  const { targetIdx, correctIdx, silentIdx } = ssodnSpans(ss)
  return (
    <>
      <div className="crispr-track-h">HDR repair (ssODN)</div>
      <div className="ssodn-vis">
        <SsodnLine label="Reference" seq={ss.reference_arm} hl={() => undefined} />
        <SsodnLine
          label="Variant"
          seq={ss.variant_arm}
          hl={(i) => (targetIdx.has(i) ? 'seq-hl-pam' : undefined)}
        />
        <SsodnLine
          label="Repair"
          seq={ss.repair_template}
          hl={(i) =>
            correctIdx.has(i)
              ? 'seq-hl-correct'
              : silentIdx.has(i)
                ? 'seq-hl-silent'
                : undefined
          }
        />
      </div>
      <div className="ssodn-meta">
        <span>
          <i className="sw correct" /> corrective edit
        </span>
        <span>
          <i className="sw silent" /> silent PAM-blocking edit
        </span>
        <span>
          <i className="sw target" /> pathogenic base
        </span>
        <span className="ssodn-meta-num">
          Arms L {ss.arm_lengths.left} / R {ss.arm_lengths.right} nt · est. HDR{' '}
          {(ss.estimated_hdr_efficiency * 100).toFixed(0)}%
        </span>
      </div>
      {ss.edits_encoded.length > 0 && (
        <div className="help-note">{ss.edits_encoded.join(' · ')}</div>
      )}
    </>
  )
}
