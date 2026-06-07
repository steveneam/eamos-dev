'use client'

import { useMemo, useState } from 'react'
import type {
  CasEnzyme,
  CrisprOffTargetRequest,
  CrisprOffTargetResponse,
  CrisprOffTargetSite,
  CrisprScreeningPrimerRequest,
  CrisprScreeningPrimerResponse,
  CrisprScreeningPrimerTarget,
} from '@/lib/backend'
import { enumerateOffTargets, designScreeningPrimers } from '@/lib/api'

interface OffTargetTabProps {
  gene: string
  cdna: string
}

/** Default protospacer used to seed the form (the de-identified on-target). */
const DEFAULT_GUIDE = 'GAGTCCGAGCAGAAGAAGAT'

type SortKey = 'score' | 'mismatches'

function clampInt(raw: string, min: number, max: number, fallback: number): number {
  const parsed = Math.round(Number(raw))
  if (!Number.isFinite(parsed)) return fallback
  return Math.min(max, Math.max(min, parsed))
}

/** CFD-like off-target score: higher = more likely to cut = more concerning. */
function offScoreClass(score: number): string {
  return score >= 0.2 ? 'score-bad' : score >= 0.05 ? 'score-mid' : 'score-good'
}

function locusLabel(site: CrisprOffTargetSite): string {
  return `${site.chromosome}:${site.position.toLocaleString()}`
}

/** A stable identity for a site within one response (used as selection key). */
function siteKey(site: CrisprOffTargetSite): string {
  return `${site.chromosome}:${site.position}:${site.strand}:${site.sequence}`
}

/**
 * Base-coloured protospacer — each A/C/G/T painted with the shared --base-*
 * tokens (same vocabulary as the Align trace / chromatogram / guide design).
 * Bases that differ from the on-target guide are ringed so mismatches read at
 * a glance. The PAM keeps the amber recognition chip.
 */
function OffTargetSeq({
  sequence,
  pam,
  onTarget,
}: {
  sequence: string
  pam: string
  onTarget: string
}) {
  return (
    <span className="seq g-seq">
      {sequence
        .toUpperCase()
        .split('')
        .map((b, i) => {
          const mm = onTarget[i] !== undefined && b !== onTarget[i].toUpperCase()
          return (
            <span
              key={i}
              className={`g-nt ${'ACGT'.includes(b) ? b : ''}${mm ? ' mm' : ''}`}
            >
              {b}
            </span>
          )
        })}
      <span className="g-pam">{pam}</span>
    </span>
  )
}

function toTSV(headers: string[], rows: Array<Array<string | number>>): string {
  const esc = (v: string | number) => String(v).replace(/\t/g, ' ').replace(/\n/g, ' ')
  return [headers.join('\t'), ...rows.map((r) => r.map(esc).join('\t'))].join('\n')
}

function downloadText(filename: string, text: string) {
  const blob = new Blob([text], { type: 'text/tab-separated-values;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** A two-purpose copy/download control for a single TSV section. */
function ExportButtons({
  label,
  filename,
  tsv,
}: {
  label: string
  filename: string
  tsv: string
}) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(tsv)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard blocked — download still works */
    }
  }
  return (
    <span className="ots-export">
      <button
        type="button"
        className="ots-export-btn"
        onClick={copy}
        title={`Copy the ${label} as tab-separated values — paste straight into Excel or Sheets.`}
      >
        {copied ? 'Copied' : `Copy ${label}`}
      </button>
      <button
        type="button"
        className="ots-export-btn"
        onClick={() => downloadText(filename, tsv)}
        title={`Download the ${label} as a .tsv file.`}
      >
        Download .tsv
      </button>
    </span>
  )
}

export function OffTargetTab({ gene, cdna }: OffTargetTabProps) {
  // ── enumeration form ──────────────────────────────────────────────────
  const [guide, setGuide] = useState(DEFAULT_GUIDE)
  const [pam, setPam] = useState('NGG')
  const [maxMismatches, setMaxMismatches] = useState(3)
  const [chrom, setChrom] = useState('chr7')
  const [pos, setPos] = useState('117509080')
  const [strand, setStrand] = useState<'+' | '-'>('+')

  const [res, setRes] = useState<CrisprOffTargetResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // ── curation ──────────────────────────────────────────────────────────
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [sort, setSort] = useState<SortKey>('score')
  const [filterMm, setFilterMm] = useState(4)
  const [codingOnly, setCodingOnly] = useState(false)
  const [topN, setTopN] = useState(10)
  const [flank, setFlank] = useState(400)

  // ── screening primers ─────────────────────────────────────────────────
  const [prefix, setPrefix] = useState('OTS')
  const [primerRes, setPrimerRes] = useState<CrisprScreeningPrimerResponse | null>(null)
  const [primerLoading, setPrimerLoading] = useState(false)
  const [primerError, setPrimerError] = useState<string | null>(null)

  const clearComputed = () => {
    setRes(null)
    setError(null)
    setSelected(new Set())
    setPrimerRes(null)
    setPrimerError(null)
  }

  const cleanGuide = guide.trim().toUpperCase()

  const enumerate = async () => {
    if (cleanGuide.length < 17 || /[^ACGT]/.test(cleanGuide)) {
      setError('Enter a protospacer of 17–20 nt using A/C/G/T only.')
      setRes(null)
      return
    }
    setLoading(true)
    setError(null)
    setRes(null)
    setSelected(new Set())
    setPrimerRes(null)
    setPrimerError(null)
    try {
      const position = Number(pos)
      const payload: CrisprOffTargetRequest = {
        guide: cleanGuide,
        pam: pam.trim().toUpperCase() || 'NGG',
        enzyme: 'SpCas9' as CasEnzyme,
        genome_build: 'GRCh38',
        max_mismatches: maxMismatches,
        on_target_locus: Number.isFinite(position)
          ? { chromosome: chrom.trim() || 'chr1', position, strand }
          : null,
      }
      const r = await enumerateOffTargets(payload)
      setRes(r)
      // Pre-select the default top-N off-targets so the flow is one click ahead.
      setSelected(autoPickKeys(r.sites, topN, 4, false))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Off-target enumeration failed')
    } finally {
      setLoading(false)
    }
  }

  const onTargetSite = res?.sites.find((s) => s.on_target) ?? null
  const offSites = useMemo(
    () => (res ? res.sites.filter((s) => !s.on_target) : []),
    [res],
  )
  const onTargetSeq = onTargetSite?.sequence ?? cleanGuide

  const visibleOff = useMemo(() => {
    const filtered = offSites.filter(
      (s) => s.mismatches <= filterMm && (!codingOnly || s.biotype === 'protein_coding'),
    )
    return [...filtered].sort((a, b) =>
      sort === 'score' ? b.score - a.score : a.mismatches - b.mismatches,
    )
  }, [offSites, filterMm, codingOnly, sort])

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
    setPrimerRes(null)
  }

  const autoPick = () => {
    setSelected(autoPickKeys(offSites, topN, filterMm, codingOnly))
    setPrimerRes(null)
  }

  const selectedSites = useMemo(
    () => offSites.filter((s) => selected.has(siteKey(s))),
    [offSites, selected],
  )

  const designPrimers = async () => {
    if (!res || selectedSites.length === 0) return
    setPrimerLoading(true)
    setPrimerError(null)
    setPrimerRes(null)
    try {
      const sites: CrisprScreeningPrimerTarget[] = selectedSites.map((s, i) => ({
        site_index: i + 1,
        chromosome: s.chromosome,
        position: s.position,
        strand: s.strand,
        sequence: s.sequence,
        pam: s.pam,
        point: `${s.chromosome}:${s.position}`,
      }))
      const payload: CrisprScreeningPrimerRequest = {
        sites,
        genome_build: res.genome_build,
        flank_bp: flank,
        naming_prefix: prefix,
        mode: 'sanger',
      }
      const r = await designScreeningPrimers(payload)
      setPrimerRes(r)
    } catch (e) {
      setPrimerError(e instanceof Error ? e.message : 'Screening-primer design failed')
    } finally {
      setPrimerLoading(false)
    }
  }

  const codingCount = offSites.filter((s) => s.biotype === 'protein_coding').length
  const closeCount = offSites.filter((s) => s.mismatches <= 1).length
  const usingMock = primerRes?.warnings.includes('crispr_screening_mock_template')

  const sitesTsv = res
    ? toTSV(
        ['#', 'Sequence', 'PAM', 'Score', 'Mismatches', 'Gene', 'Gene ID', 'Biotype', 'Chromosome', 'Strand', 'Position', 'On-target'],
        res.sites.map((s, i) => [
          s.on_target ? 'on-target' : i,
          s.sequence,
          s.pam,
          s.score,
          s.mismatches,
          s.gene ?? 'intergenic',
          s.gene_id ?? '',
          s.biotype ?? '',
          s.chromosome,
          s.strand,
          s.position,
          s.on_target ? 'yes' : 'no',
        ]),
      )
    : ''

  const primersTsv = primerRes
    ? toTSV(
        ['Site', 'Point', 'Region', 'Name F', 'Forward', 'Name R', 'Reverse', 'Tm F', 'Tm R', 'GC F', 'GC R', 'Product', 'Other products'],
        primerRes.primers.map((p) => [
          p.site_index,
          p.point,
          p.region,
          p.name_forward,
          p.forward,
          p.name_reverse,
          p.reverse,
          p.tm_forward,
          p.tm_reverse,
          p.gc_forward,
          p.gc_reverse,
          p.product_size,
          p.other_products,
        ]),
      )
    : ''

  return (
    <div className="crispr-design">
      <div className="tool-form">
        <label className="field ots-field-wide">
          <span className="field-label">Guide protospacer (5′→3′)</span>
          <input
            className="field-input mono"
            type="text"
            value={guide}
            spellCheck={false}
            disabled={loading}
            onChange={(e) => {
              setGuide(e.target.value)
              clearComputed()
            }}
          />
        </label>
        <label className="field">
          <span className="field-label">PAM</span>
          <input
            className="field-input mono"
            type="text"
            value={pam}
            spellCheck={false}
            disabled={loading}
            onChange={(e) => {
              setPam(e.target.value)
              clearComputed()
            }}
          />
        </label>
        <label className="field">
          <span className="field-label">Max mismatches</span>
          <input
            className="field-input"
            type="number"
            min={0}
            max={4}
            value={maxMismatches}
            disabled={loading}
            onChange={(e) => {
              setMaxMismatches(clampInt(e.target.value, 0, 4, maxMismatches))
              clearComputed()
            }}
          />
        </label>
        <label className="field">
          <span className="field-label">On-target chromosome</span>
          <input
            className="field-input mono"
            type="text"
            value={chrom}
            spellCheck={false}
            disabled={loading}
            onChange={(e) => {
              setChrom(e.target.value)
              clearComputed()
            }}
          />
        </label>
        <label className="field">
          <span className="field-label">On-target position</span>
          <input
            className="field-input mono"
            type="text"
            value={pos}
            spellCheck={false}
            disabled={loading}
            onChange={(e) => {
              setPos(e.target.value)
              clearComputed()
            }}
          />
        </label>
        <label className="field">
          <span className="field-label">Strand</span>
          <select
            className="field-select"
            value={strand}
            disabled={loading}
            onChange={(e) => {
              setStrand(e.target.value as '+' | '-')
              clearComputed()
            }}
          >
            <option value="+">Plus (+)</option>
            <option value="-">Minus (−)</option>
          </select>
        </label>
      </div>

      <div className="btn-row">
        <button
          type="button"
          className="btn-teal"
          onClick={enumerate}
          disabled={loading}
          title="Search the genome for sites matching your guide + PAM within the mismatch limit, then score and rank them."
        >
          {loading ? 'Enumerating…' : 'Enumerate off-targets'}
        </button>
        <span className="tool-panel-sub">
          {gene} · {cdna} · SpCas9 NGG · GRCh38
        </span>
      </div>

      <div className="help-note">
        Paste the protospacer (spacer, ~20 nt) of a guide designed above. Mock
        Cas-OFFinder genome search scored CFD-style; the on-target row is pinned.
        Loci are de-identified sample coordinates — connect the backend for a
        real GRCh38 search.
      </div>

      {error && <div className="crispr-error">{error}</div>}

      {res && (
        <>
          <div
            className="crispr-summary"
            role="group"
            aria-label="Off-target summary"
          >
            <div
              className="cs-cell"
              title="Total predicted off-target sites found for this guide (excluding the on-target site)."
            >
              <span className="cs-k">Sites found</span>
              <span className="cs-v">{offSites.length}</span>
            </div>
            <div
              className="cs-cell"
              title="Off-targets that fall inside a protein-coding gene — usually the highest priority to screen."
            >
              <span className="cs-k">Coding</span>
              <span className="cs-v">{codingCount}</span>
            </div>
            <div
              className="cs-cell"
              title="Off-targets within one mismatch of your guide — the closest sequence matches, most likely to be cut."
            >
              <span className="cs-k">≤1 mismatch</span>
              <span className="cs-v">{closeCount}</span>
            </div>
            <div
              className="cs-cell"
              title="How many off-target sites you've ticked to design screening primers for."
            >
              <span className="cs-k">Selected</span>
              <span className="cs-v">{selectedSites.length}</span>
            </div>
          </div>

          {onTargetSite && (
            <div className="crispr-ref-anchor">
              <span className="cra-label">On-target</span>
              <span className="cra-target">
                <OffTargetSeq
                  sequence={onTargetSite.sequence}
                  pam={onTargetSite.pam}
                  onTarget={onTargetSeq}
                />
              </span>
              <span className="cra-meta">
                {locusLabel(onTargetSite)} ({onTargetSite.strand}) · intended cut
              </span>
            </div>
          )}

          <div className="crispr-table-bar">
            <div className="seg" role="group" aria-label="Sort off-targets">
              <button
                type="button"
                className={sort === 'score' ? 'active' : ''}
                onClick={() => setSort('score')}
                title="Sort by off-target score, highest first — the CFD-style predicted cutting likelihood. The riskiest sites to validate go to the top."
                aria-label="Sort by off-target score, highest first"
              >
                Score high
              </button>
              <button
                type="button"
                className={sort === 'mismatches' ? 'active' : ''}
                onClick={() => setSort('mismatches')}
                title="Sort by number of mismatches vs your guide, fewest first — closer sequences are more likely to be cut."
                aria-label="Sort by mismatches versus the guide, fewest first"
              >
                Mismatches low
              </button>
            </div>
            <div className="ots-curate">
              <label
                className="ots-curate-field"
                title="How many top-ranked off-targets the Auto-pick button selects."
              >
                <span className="field-label">Top-N</span>
                <input
                  type="number"
                  min={1}
                  max={Math.max(50, offSites.length)}
                  value={topN}
                  onChange={(e) =>
                    setTopN(clampInt(e.target.value, 1, Math.max(50, offSites.length), topN))
                  }
                />
              </label>
              <button
                type="button"
                className="ots-export-btn"
                onClick={autoPick}
                title="Select the top-N off-targets by score (always including any ≤1-mismatch site), honouring the filters."
              >
                Auto-pick top {topN}
              </button>
              <label
                className="ots-curate-field"
                title="Hide off-targets with more than this many mismatches versus your guide."
              >
                <span className="field-label">Max mm</span>
                <input
                  type="number"
                  min={0}
                  max={4}
                  value={filterMm}
                  onChange={(e) => setFilterMm(clampInt(e.target.value, 0, 4, filterMm))}
                />
              </label>
              <label
                className="ots-curate-check"
                title="Show only off-targets that fall inside a protein-coding gene."
              >
                <input
                  type="checkbox"
                  checked={codingOnly}
                  onChange={(e) => setCodingOnly(e.target.checked)}
                />
                Coding only
              </label>
            </div>
          </div>

          <div className="crispr-table-wrap">
            <table className="tool-table">
              <thead>
                <tr>
                  <th aria-label="Select" title="Tick to include this site in screening-primer design." />
                  <th title="Rank within the filtered off-target list.">#</th>
                  <th title="CFD-style off-target score (0–1): predicted likelihood the guide cuts here. Higher = more concerning.">
                    Score
                  </th>
                  <th title="Number of mismatches between this site and your guide spacer (fewer = closer match).">
                    MM
                  </th>
                  <th title="The off-target 20-mer (5′→3′) + PAM. Bases that differ from your guide are underlined.">
                    Off-target 5′→3′ + PAM
                  </th>
                  <th title="Gene the off-target falls in (or intergenic if none).">Gene</th>
                  <th title="Gene biotype — protein-coding hits are usually the priority to screen.">
                    Biotype
                  </th>
                  <th title="Genomic position of the off-target site (chromosome:position, GRCh38).">Locus</th>
                  <th title="DNA strand the off-target sits on (+ plus / − minus).">Strand</th>
                </tr>
              </thead>
              <tbody>
                {onTargetSite && (
                  <tr className="ots-on-target">
                    <td />
                    <td className="num">on</td>
                    <td className="num score-good">1.000</td>
                    <td className="num">0</td>
                    <td className="seq">
                      <OffTargetSeq
                        sequence={onTargetSite.sequence}
                        pam={onTargetSite.pam}
                        onTarget={onTargetSeq}
                      />
                    </td>
                    <td>on-target</td>
                    <td>—</td>
                    <td className="mono">{locusLabel(onTargetSite)}</td>
                    <td className="num">{onTargetSite.strand}</td>
                  </tr>
                )}
                {visibleOff.map((s, i) => {
                  const key = siteKey(s)
                  const isSel = selected.has(key)
                  return (
                    <tr key={key} className={isSel ? 'selected' : undefined}>
                      <td>
                        <input
                          className="row-cb"
                          type="checkbox"
                          checked={isSel}
                          onChange={() => toggle(key)}
                          aria-label={`Select off-target ${i + 1}`}
                        />
                      </td>
                      <td className="num">{i + 1}</td>
                      <td className={`num ${offScoreClass(s.score)}`}>
                        {s.score.toFixed(3)}
                      </td>
                      <td className="num">{s.mismatches}</td>
                      <td className="seq">
                        <OffTargetSeq sequence={s.sequence} pam={s.pam} onTarget={onTargetSeq} />
                      </td>
                      <td>{s.gene ?? <span className="cra-meta">intergenic</span>}</td>
                      <td>
                        {s.biotype ? (
                          <span
                            className={`ots-biotype${s.biotype === 'protein_coding' ? ' coding' : ''}`}
                          >
                            {s.biotype.replace(/_/g, ' ')}
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="mono">{locusLabel(s)}</td>
                      <td className="num">{s.strand}</td>
                    </tr>
                  )
                })}
                {visibleOff.length === 0 && (
                  <tr>
                    <td colSpan={9} className="crispr-empty">
                      No off-targets within {filterMm} mismatches
                      {codingOnly ? ' in coding genes' : ''}.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="ots-actions">
            <span className="ots-export-label">Export all sites</span>
            <ExportButtons
              label="sites"
              filename={`${gene}_offtargets.tsv`}
              tsv={sitesTsv}
            />
          </div>

          <div className="crispr-track-h">Screening primers</div>
          <div className="ots-screen-bar">
            <label
              className="ots-curate-field"
              title="Half-width of the screening window drawn around each off-target site — primers flank the cut point by ± this many bp."
            >
              <span className="field-label">Flank (± bp)</span>
              <input
                type="number"
                min={50}
                max={2000}
                step={50}
                value={flank}
                onChange={(e) => {
                  setFlank(clampInt(e.target.value, 50, 2000, flank))
                  setPrimerRes(null)
                }}
              />
            </label>
            <label
              className="ots-curate-field"
              title="Prefix for the generated primer names, e.g. OTS → OTS_1_F / OTS_1_R."
            >
              <span className="field-label">Name prefix</span>
              <input
                className="mono"
                type="text"
                value={prefix}
                spellCheck={false}
                onChange={(e) => {
                  setPrefix(e.target.value)
                  setPrimerRes(null)
                }}
              />
            </label>
            <button
              type="button"
              className="btn-teal"
              onClick={designPrimers}
              disabled={primerLoading || selectedSites.length === 0}
              title="Design a PCR primer pair to amplify and Sanger-screen each selected off-target window."
            >
              {primerLoading
                ? 'Designing…'
                : `Design primers for ${selectedSites.length} site${selectedSites.length === 1 ? '' : 's'}`}
            </button>
          </div>

          {selectedSites.length === 0 && (
            <div className="help-note">
              Select off-target sites above (or Auto-pick) to draw ±{flank} bp
              screening windows and design PCR primers for each.
            </div>
          )}

          {primerError && <div className="crispr-error">{primerError}</div>}

          {primerRes && (
            <>
              {usingMock && (
                <div className="crispr-result-note">
                  Offline demo: screening primers are drawn from the bundled
                  primer fixture over mock windows. Connect the backend for
                  windows resolved against the real GRCh38 reference.
                </div>
              )}
              <div className="crispr-table-wrap">
                <table className="tool-table ots-primer-table">
                  <thead>
                    <tr>
                      <th title="Selected off-target index — matches the OTS_n primer name.">Site</th>
                      <th title="The off-target cut point being screened (chromosome:position).">Point</th>
                      <th title="Reference window the primers were designed against (chrN:start–end).">
                        Window
                      </th>
                      <th title="Forward (top) / reverse (bottom) primer names.">Name F / R</th>
                      <th title="Forward (top) and reverse (bottom) primer sequences, 5′→3′.">
                        Forward / Reverse 5′→3′
                      </th>
                      <th title="Melting temperature of each primer in °C — forward over reverse.">Tm</th>
                      <th title="GC content of each primer — forward over reverse.">GC%</th>
                      <th title="Expected PCR amplicon size in base pairs.">Product</th>
                      <th title="In-silico PCR specificity — NONE = a single clean amplicon; otherwise alternate products were predicted.">
                        Other products
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {primerRes.primers.map((p) => (
                      <tr key={p.site_index} className={p.recommended ? 'selected' : undefined}>
                        <td className="num">
                          {p.recommended ? '★ ' : ''}
                          {p.site_index}
                        </td>
                        <td className="mono">{p.point}</td>
                        <td className="mono">{p.region}</td>
                        <td className="mono ots-names">
                          <div>{p.name_forward}</div>
                          <div>{p.name_reverse}</div>
                        </td>
                        <td className="seq ots-primer-seq">
                          <div>{p.forward}</div>
                          <div>{p.reverse}</div>
                        </td>
                        <td className="num">
                          <div>{p.tm_forward.toFixed(1)}</div>
                          <div>{p.tm_reverse.toFixed(1)}</div>
                        </td>
                        <td className="num">
                          <div>{p.gc_forward}</div>
                          <div>{p.gc_reverse}</div>
                        </td>
                        <td className="num">{p.product_size} bp</td>
                        <td
                          className={p.other_products === 'NONE' ? 'score-good' : 'score-mid'}
                        >
                          {p.other_products}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="ots-actions">
                <span className="ots-export-label">Export screening panel</span>
                <ExportButtons
                  label="primers"
                  filename={`${gene}_screening_primers.tsv`}
                  tsv={primersTsv}
                />
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}

/** Pick the top-N off-targets by score (after mismatch / coding filters). */
function autoPickKeys(
  sites: CrisprOffTargetSite[],
  n: number,
  maxMm: number,
  codingOnly: boolean,
): Set<string> {
  const eligible = sites
    .filter((s) => !s.on_target && s.mismatches <= maxMm)
    .filter((s) => !codingOnly || s.biotype === 'protein_coding')
    .sort((a, b) => b.score - a.score)
  // Always include any ≤1-mismatch site, then fill to N by score.
  const close = eligible.filter((s) => s.mismatches <= 1)
  const picked = new Set(close.map(siteKey))
  for (const s of eligible) {
    if (picked.size >= n) break
    picked.add(siteKey(s))
  }
  return picked
}
