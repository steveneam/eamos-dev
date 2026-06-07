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

interface DesignTabProps {
  gene: string
  cdna: string
}

const CAS_OPTIONS: Array<{
  value: CasEnzyme
  label: string
  caveat: string
  disabled?: boolean
}> = [
  {
    value: 'SpCas9',
    label: 'SpCas9 NGG',
    caveat:
      'Current real-mode CRISPR design supports local deterministic SpCas9 only.',
  },
  {
    value: 'SaCas9',
    label: 'SaCas9 (unavailable)',
    caveat:
      'SaCas9 remains a schema value only; the real-mode backend rejects it until a provider is added.',
    disabled: true,
  },
  {
    value: 'Cas12a',
    label: 'Cas12a (unavailable)',
    caveat:
      'Generic Cas12a is not a source-backed DeepCpf1/enCas12a provider in the current backend.',
    disabled: true,
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

/** Lower off-target is better in the current fixture contract. */
function offClass(v: number): string {
  return v < 20 ? 'score-good' : v <= 30 ? 'score-mid' : 'score-bad'
}
function onClass(v: number): string {
  return v >= 75 ? 'score-good' : v >= 60 ? 'score-mid' : 'score-bad'
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

export function DesignTab({ gene, cdna }: DesignTabProps) {
  const [cas, setCas] = useState<CasEnzyme>('SpCas9')
  const [strand, setStrand] = useState<CrisprRequest['strand_filter']>('both')
  const [offTol, setOffTol] = useState(2)
  const [minOnTarget, setMinOnTarget] = useState(0)
  const [sort, setSort] = useState<SortKey>(null)

  const [res, setRes] = useState<CrisprResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hovered, setHovered] = useState<number | null>(null)

  const selectedCas = CAS_OPTIONS.find((option) => option.value === cas)
  const unavailableCas = CAS_OPTIONS.filter((option) => option.disabled)
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
        <label className="field">
          <span className="field-label">Cas enzyme</span>
          <select
            className="field-select"
            value={cas}
            disabled={loading}
            onChange={(e) => {
              const nextCas = e.target.value as CasEnzyme
              if (nextCas !== 'SpCas9') return
              setCas(nextCas)
              clearComputed()
            }}
          >
            {CAS_OPTIONS.map((c) => (
              <option key={c.value} value={c.value} disabled={c.disabled}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
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
        <label className="field">
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
        <label className="field">
          <span className="field-label">Target window</span>
          <input
            className="field-input"
            type="text"
            value="server-resolved"
            disabled
            readOnly
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
        {unavailableCas.map((option) => (
          <div className="help-note" key={option.value}>
            {option.caveat}
          </div>
        ))}
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
              >
                Default
              </button>
              <button
                type="button"
                className={sort === 'on' ? 'active' : ''}
                onClick={() => setSort('on')}
              >
                On-target high
              </button>
              <button
                type="button"
                className={sort === 'off' ? 'active' : ''}
                onClick={() => setSort('off')}
              >
                Off-target low
              </button>
            </div>
            <label className="crispr-minfilter">
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
            (template-relative offsets), not genomic coordinates.
          </div>

          <div className="crispr-table-wrap">
            <table className="tool-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Strand</th>
                  <th>Guide 5′ to 3′ + PAM</th>
                  <th>On-target</th>
                  <th>Off-target</th>
                  <th>GC%</th>
                  <th>Region</th>
                  <th>Notes</th>
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
                      <td className={`num ${onClass(g.on_target_score)}`}>
                        {g.on_target_score.toFixed(1)}
                      </td>
                      <td className={`num ${offClass(g.off_target_score)}`}>
                        {g.off_target_score.toFixed(1)}
                      </td>
                      <td className="num">{g.gc_percent}</td>
                      <td>
                        {gene} <span className="cra-meta">tmpl</span>
                      </td>
                      <td>{g.notes}</td>
                    </tr>
                  )
                })}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={10} className="crispr-empty">
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
