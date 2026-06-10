'use client'

import { useMemo, useState } from 'react'
import type {
  CasEnzyme,
  CrisprRequest,
  CrisprResponse,
  HdrSsodn,
} from '@/lib/backend'
import { designGuides } from '@/lib/api'
import { designProviderDisclosure } from '@/lib/workbench/crispr-disclosure'
import { recommendedGuideIndex } from '@/lib/workbench/crispr-guide-ranking'
import { mapGuide } from '@/lib/workbench/crispr-guide-map'
import { GuideTrack } from './GuideTrack'
import { SsodnLabDonor } from './SsodnLabDonor'
import { ScoreBullet } from '../ScoreBullet'
import { IconScope } from '@/components/icons/Icon'
import type { ScreenSeed } from './CrisprPanel'

interface DesignTabProps {
  gene: string
  cdna: string
  /** Hand a designed guide to the Off-targets tab for genome-wide screening. */
  onScreenGuide?: (seed: ScreenSeed) => void
}

const CAS_OPTIONS: Array<{ value: CasEnzyme; label: string; caveat: string }> = [
  {
    value: 'SpCas9',
    label: 'SpCas9 · NGG',
    caveat:
      'Current real-mode CRISPR design supports local deterministic SpCas9 only.',
  },
]

const STRANDS: Array<{ v: CrisprRequest['strand_filter']; label: string }> = [
  { v: 'both', label: 'Both strands' },
  { v: 'plus', label: 'Plus (+) only' },
  { v: 'minus', label: 'Minus (-) only' },
]

type SortKey = 'on' | 'off' | null

function clampNumber(
  raw: string,
  min: number,
  max: number,
  fallback: number,
): number {
  const parsed = Number(raw)
  if (!Number.isFinite(parsed)) return fallback
  return Math.min(max, Math.max(min, parsed))
}

/** SpCas9 recognises NGG; the other enzymes stay schema-only in real mode. */
function casPam(cas: CasEnzyme): string {
  return cas === 'SpCas9' ? 'NGG' : '—'
}

/**
 * Colour-coded guide spacer — each A/C/G/T painted with the shared --base-*
 * tokens (same vocabulary as the Align trace, chromatogram, and gene viewer),
 * so the 20-mer reads consistently across the Workbench. The PAM keeps its
 * amber recognition chip. Letters stay visible, so colour is never the only cue.
 */
function GuideSeq({ guide, pam }: { guide: string; pam: string }) {
  return (
    <span className="seq g-seq">
      {guide
        .toUpperCase()
        .split('')
        .map((b, i) => (
          <span key={i} className={`g-nt ${'ACGT'.includes(b) ? b : ''}`}>
            {b}
          </span>
        ))}
      <span className="g-pam">{pam}</span>
    </span>
  )
}

/** ssODN highlight classes, derived from the three-arm diff. */
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

export function DesignTab({ gene, cdna, onScreenGuide }: DesignTabProps) {
  const [cas] = useState<CasEnzyme>('SpCas9')
  const [strand, setStrand] = useState<CrisprRequest['strand_filter']>('both')
  const [offTol, setOffTol] = useState(2)
  const [minOnTarget, setMinOnTarget] = useState(0)
  const [sort, setSort] = useState<SortKey>(null)

  const [res, setRes] = useState<CrisprResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hovered, setHovered] = useState<number | null>(null)

  const selectedCas = CAS_OPTIONS.find((option) => option.value === cas)
  const providerDisclosure = designProviderDisclosure(res)

  const clearComputed = () => {
    setRes(null)
    setError(null)
    setHovered(null)
  }

  const run = async () => {
    if (!Number.isFinite(offTol) || offTol < 0 || offTol > 5) {
      setError('Off-target tolerance must be between 0 and 5.')
      setRes(null)
      setHovered(null)
      return
    }

    setLoading(true)
    setError(null)
    setRes(null)
    setHovered(null)
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
      const nextRec = recommendedGuideIndex(r.guides)
      setHovered(nextRec >= 0 ? nextRec : null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'CRISPR design failed')
    } finally {
      setLoading(false)
    }
  }

  const recIdx = res ? recommendedGuideIndex(res.guides) : -1
  const plusCount = res ? res.guides.filter((g) => g.strand === '+').length : 0
  const minusCount = res ? res.guides.length - plusCount : 0
  const bestOn =
    res && res.guides.length
      ? Math.max(...res.guides.map((g) => g.on_target_score))
      : null
  const bestOff =
    res && res.guides.length
      ? Math.min(...res.guides.map((g) => g.off_target_score))
      : null

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
    (hovered == null ? null : rows.find((g) => g.index === hovered)) ??
    rows[0] ??
    null
  const template = res?.ssodn?.reference_arm ?? null
  const returnedDifferentCas = Boolean(res && res.cas !== cas)

  return (
    <div className="crispr-design">
      <div className="tool-form">
        <div className="field">
          <span className="field-label">Cas enzyme</span>
          <span className="crispr-enzyme-chip">SpCas9 · NGG</span>
        </div>
        <label className="field">
          <span className="field-label">Strand</span>
          <select
            className="field-select"
            value={strand}
            disabled={loading}
            onChange={(e) => {
              setStrand(e.target.value as CrisprRequest['strand_filter'])
              clearComputed()
            }}
          >
            {STRANDS.map((s) => (
              <option key={s.v} value={s.v}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label
          className="field"
          title="Maximum mismatches tolerated when scoring off-target risk for each guide (0–5)."
        >
          <span className="field-label">Off-target tolerance</span>
          <input
            className="field-input"
            type="number"
            min={0}
            max={5}
            value={offTol}
            disabled={loading}
            onChange={(e) => {
              setOffTol(clampNumber(e.target.value, 0, 5, offTol))
              clearComputed()
            }}
          />
        </label>
      </div>

      <div className="btn-row">
        <button
          type="button"
          className="btn-teal"
          onClick={run}
          disabled={loading}
          title="Design SpCas9 (NGG) guides across the target window"
        >
          {loading ? 'Designing...' : 'Design SpCas9 guides'}
        </button>
        <span className="tool-panel-sub">
          {gene} / {cdna} / {providerDisclosure.providerLabel}
        </span>
      </div>

      <div className="crispr-caveats">
        <div className="help-note">
          Provider: {providerDisclosure.providerLabel}.{' '}
          {providerDisclosure.statusLine}
        </div>
        <div className="help-note">{providerDisclosure.scoreLine}</div>
        <div className="help-note">{providerDisclosure.platformLine}</div>
        {selectedCas && <div className="help-note">{selectedCas.caveat}</div>}
      </div>

      {error && <div className="crispr-error">{error}</div>}

      {res && (
        <>
          {returnedDifferentCas && (
            <div className="crispr-result-note">
              Returned result is labeled {res.cas}; treat this as sample output
              for the requested {cas} mode.
            </div>
          )}

          <div className="crispr-ref-anchor">
            <span className="cra-label">Designed against</span>
            <span className="cra-target">
              {gene} · {cdna}
            </span>
            {template && (
              <span className="cra-meta">
                template {template.length} nt · ssODN reference arm
              </span>
            )}
          </div>

          <div
            className="crispr-summary"
            role="group"
            aria-label="Candidate summary"
          >
            <div className="cs-cell">
              <span className="cs-k">Candidates found</span>
              <span className="cs-v">{res.guides.length}</span>
            </div>
            <div className="cs-cell">
              <span className="cs-k">Enzyme</span>
              <span className="cs-v">
                {res.cas} · {casPam(res.cas)}
              </span>
            </div>
            <div className="cs-cell">
              <span className="cs-k">Passing filter</span>
              <span className="cs-v">{rows.length}</span>
            </div>
            <div className="cs-cell">
              <span className="cs-k">Strand</span>
              <span className="cs-v">
                {plusCount} (+) / {minusCount} (−)
              </span>
            </div>
            <div className="cs-cell">
              <span className="cs-k">Best on-target</span>
              <span className="cs-v">
                {bestOn != null ? bestOn.toFixed(1) : '—'}
              </span>
            </div>
            <div className="cs-cell">
              <span className="cs-k">Best off-target</span>
              <span className="cs-v">
                {bestOff != null ? bestOff.toFixed(1) : '—'}
              </span>
            </div>
            {recIdx >= 0 && (
              <div className="cs-cell">
                <span className="cs-k">Recommended</span>
                <span className="cs-v">#{recIdx} ★</span>
              </div>
            )}
          </div>

          <div className="crispr-table-bar">
            <div className="seg" role="group" aria-label="Sort guides">
              <button
                type="button"
                className={sort === null ? 'active' : ''}
                onClick={() => setSort(null)}
                title="Keep the design engine's original guide order."
              >
                Default
              </button>
              <button
                type="button"
                className={sort === 'on' ? 'active' : ''}
                onClick={() => setSort('on')}
                title="Sort by on-target score, highest first — the predicted cutting efficiency at the intended site."
                aria-label="Sort by on-target score, highest first"
              >
                On-target high
              </button>
              <button
                type="button"
                className={sort === 'off' ? 'active' : ''}
                onClick={() => setSort('off')}
                title="Sort by off-target score, lowest first — fewer/weaker predicted off-target sites is safer."
                aria-label="Sort by off-target score, lowest first"
              >
                Off-target low
              </button>
            </div>
            <label
              className="crispr-minfilter"
              title="Hide guides whose on-target efficiency score is below this value."
            >
              <span className="field-label">
                Min on-target &gt;= {minOnTarget}
              </span>
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

          <div className="help-note">
            Start / End / Region are positions on the design template
            (template-relative offsets), not genomic coordinates. The design
            window is resolved on the server from the selected gene / cDNA.
          </div>

          <div className="crispr-table-wrap">
            <table className="tool-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Start</th>
                  <th>End</th>
                  <th title="Which DNA strand the guide targets (+ plus / − minus).">Strand</th>
                  <th title="The 20-nt spacer (5′→3′) plus its PAM; bases are colour-coded and the PAM carries the amber recognition chip.">
                    Guide 5′ to 3′ + PAM
                  </th>
                  <th title="On-target score — predicted cutting efficiency at the intended site (higher is better).">
                    On-target (0–100)
                  </th>
                  <th title="Off-target score — predicted risk of cutting elsewhere; lower is safer in this local surface.">
                    Off-target (lower safer)
                  </th>
                  <th title="GC content of the 20-nt spacer (≈40–70% is the usual sweet spot).">GC%</th>
                  <th title="Where the guide sits on the design template (template-relative, not a genomic coordinate).">
                    Region
                  </th>
                  <th>Notes</th>
                  <th title="Screen this guide for genome-wide off-targets.">Screen</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((g) => {
                  const gm = template ? mapGuide(g, template) : null
                  const located = Boolean(gm?.located)
                  return (
                    <tr
                      key={g.index}
                      className={g.index === recIdx ? 'selected' : undefined}
                      onMouseEnter={() => setHovered(g.index)}
                      onFocus={() => setHovered(g.index)}
                      tabIndex={0}
                    >
                      <td className="num">
                        {g.index === recIdx ? 'rec. ' : ''}
                        {g.index}
                      </td>
                      <td className="num">
                        {located ? (gm as NonNullable<typeof gm>).spacerStart + 1 : '—'}
                      </td>
                      <td className="num">
                        {located ? (gm as NonNullable<typeof gm>).spacerEnd : '—'}
                      </td>
                      <td className="num">{g.strand}</td>
                      <td className="seq">
                        <GuideSeq guide={g.guide} pam={g.pam} />
                      </td>
                      <td className="num">
                        <ScoreBullet
                          value={g.on_target_score}
                          min={0}
                          max={100}
                          thresholds={[60, 75]}
                          sense="higher-better"
                          display={g.on_target_score.toFixed(1)}
                          muted={!providerDisclosure.sourceBacked}
                          title={`On-target ${g.on_target_score.toFixed(1)} / 100 (higher better)`}
                        />
                      </td>
                      <td className="num">
                        <ScoreBullet
                          value={g.off_target_score}
                          min={0}
                          max={50}
                          thresholds={[20, 30]}
                          sense="lower-better"
                          display={g.off_target_score.toFixed(1)}
                          muted={!providerDisclosure.sourceBacked}
                          title={`Off-target ${g.off_target_score.toFixed(1)} (lower safer)`}
                        />
                      </td>
                      <td className="num">
                        <ScoreBullet
                          value={g.gc_percent}
                          min={0}
                          max={100}
                          thresholds={[40, 70]}
                          sense="band"
                          display={String(g.gc_percent)}
                          title={`GC ${g.gc_percent}% (40–70% sweet spot)`}
                        />
                      </td>
                      <td>
                        {gene} <span className="cra-meta">tmpl</span>
                      </td>
                      <td>{g.notes}</td>
                      <td>
                        <button
                          type="button"
                          className="ots-export-btn crispr-screen-btn"
                          onClick={() =>
                            onScreenGuide?.({
                              guide: g.guide,
                              pam: g.pam,
                              strand: g.strand,
                              source: `guide #${g.index}`,
                            })
                          }
                          title="Screen this guide for genome-wide off-targets — switches to the Off-targets tab and pre-fills the protospacer + PAM."
                        >
                          Screen <IconScope size={12} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={11} className="crispr-empty">
                      No guides at min on-target &gt;= {minOnTarget}.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {activeGuide && (
            <>
              <div className="crispr-track-h">
                Guide {activeGuide.index} on design template
              </div>
              <GuideTrack
                guide={activeGuide}
                template={template}
                showCut={res.cas === 'SpCas9'}
              />
            </>
          )}

          {res.ssodn && <SsodnBlock ss={res.ssodn} />}

          {/* The lab-order donor follows guide design — you choose a guide,
              then order the ssODN repair template that pairs with it. */}
          <SsodnLabDonor gene={gene} cdna={cdna} />
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
        <SsodnLine
          label="Reference"
          seq={ss.reference_arm}
          hl={() => undefined}
        />
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
          Arms L {ss.arm_lengths.left} / R {ss.arm_lengths.right} nt / est. HDR{' '}
          {(ss.estimated_hdr_efficiency * 100).toFixed(0)}%
        </span>
      </div>
      {ss.edits_encoded.length > 0 && (
        <div className="help-note">{ss.edits_encoded.join(' / ')}</div>
      )}
    </>
  )
}
