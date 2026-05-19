import { useState } from 'react'
import type { WorkbenchTool } from '@/lib/backend'
import { aaThree } from '@/lib/workbench/codon-table'
import type { GeneWindowData } from '@/lib/workbench/gene-window'
import { TOOL_META } from './tools'
import type { ScratchEntry } from './viewer/SequenceViewerV2'
import type { SelectionSummary } from './viewer/viewer-types'

// FE-5.6 item 1: the ClinVar/gnomAD links moved out of the context strip into
// the Active variant card. Fixture-level constant (RPE65 c.260A>G), same
// pattern as `RPE65_CTX` in WorkbenchPage — per-variant wiring lands with the
// report payload in a later milestone.
const VARIANT_LINKS = [
  { label: 'ClinVar', href: 'https://www.ncbi.nlm.nih.gov/clinvar/variation/99473/' },
  { label: 'gnomAD', href: 'https://gnomad.broadinstitute.org' },
]

interface SidePanelProps {
  tool: WorkbenchTool
  data: GeneWindowData
  scratch: ScratchEntry[]
  selection: SelectionSummary | null
  collapsed: boolean
  exonTableOpen: boolean
  activeExon: number
  onToggleCollapsed: () => void
  onToggleExonTable: () => void
  onResetAll: () => void
  onJumpToExon: (n: number) => void
  onDelSelection: () => void
  onReplaceSelection: (seq: string) => void
  onClearSelection: () => void
}

function Kv({ k, v, tone }: { k: string; v: string; tone?: 'warn' | 'ok' }) {
  return (
    <div className="kv-row">
      <div className="k">{k}</div>
      <div className={tone ? `v ${tone}` : 'v'}>{v}</div>
    </div>
  )
}

function Section({
  title,
  meta,
  children,
}: {
  title: string
  meta?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="side-section">
      <h3 className="side-h">
        {title}
        {meta}
      </h3>
      {children}
    </div>
  )
}

function FeatRow({ rg, lb, rt }: { rg: string; lb: string; rt: string }) {
  return (
    <div className="side-feat-row">
      <span className="rg">{rg}</span>
      <span className="lb">{lb}</span>
      <span className="rt">{rt}</span>
    </div>
  )
}

/** Selection summary + range actions — the edit hub absorbed from the
 *  removed canvas SelectionBar (FE-5.6 Unit C). Single base: shows the
 *  reference + edit-key hints; range: delete / replace / clear. */
function SelectionBlock({
  selection,
  onDel,
  onReplace,
  onClear,
}: {
  selection: SelectionSummary
  onDel: () => void
  onReplace: (seq: string) => void
  onClear: () => void
}) {
  const [replace, setReplace] = useState('')
  const submitReplace = () => {
    const v = replace.toUpperCase().replace(/[^ATCG]/g, '')
    if (v) {
      onReplace(v)
      setReplace('')
    }
  }

  if (selection.len === 1) {
    return (
      <div className="scratch-sel">
        <div className="scratch-sel-head">
          <span className="lbl">Selection</span>
          <span className="pos">{selection.loPos}</span>
        </div>
        <div className="scratch-sel-meta">
          ref <b>{selection.refBase}</b>
          {selection.hasEdit ? ' · edited' : ''}
        </div>
        <div className="scratch-sel-hint">
          Right-click this base in the canvas to edit it. With it selected,
          press <b>A/T/C/G</b> to substitute or <b>⌫</b> to delete.
        </div>
        <div className="scratch-sel-actions">
          <button type="button" className="scratch-sel-btn ghost" onClick={onClear}>
            Clear
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="scratch-sel">
      <div className="scratch-sel-head">
        <span className="lbl">Range · {selection.len} bp</span>
        <span className="pos">
          {selection.loPos} → {selection.hiPos}
        </span>
      </div>
      <div className="scratch-sel-meta">{selection.span}</div>
      <div className="scratch-sel-actions">
        <button type="button" className="scratch-sel-btn del" onClick={onDel}>
          Delete {selection.len} bases
        </button>
        <button type="button" className="scratch-sel-btn ghost" onClick={onClear}>
          Clear
        </button>
      </div>
      <div className="scratch-sel-replace">
        <input
          className="scratch-sel-input"
          placeholder={`Replace with… (max ${selection.len * 2} bp)`}
          aria-label="Replacement sequence"
          spellCheck={false}
          value={replace}
          onChange={(e) => setReplace(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              submitReplace()
            }
          }}
        />
        <button type="button" className="scratch-sel-btn ins" onClick={submitReplace}>
          Replace →
        </button>
      </div>
    </div>
  )
}

function ViewerSide({
  data,
  scratch,
  selection,
  exonTableOpen,
  activeExon,
  onToggleExonTable,
  onResetAll,
  onJumpToExon,
  onDelSelection,
  onReplaceSelection,
  onClearSelection,
}: Omit<SidePanelProps, 'tool' | 'collapsed' | 'onToggleCollapsed'>) {
  const qv = data.queriedVariant
  const g = data.genomicCoords
  const pf = data.proteinFeatures

  return (
    <>
      <Section title="Active variant">
        <div className="kv-list">
          <Kv k="HGVS (c.)" v={qv.hgvsC} tone="warn" />
          <Kv k="HGVS (p.)" v={qv.hgvsP} tone="warn" />
          <Kv
            k="Codon"
            v={`${qv.codonNumber} (${aaThree[qv.aaRef]} → ${aaThree[qv.aaAlt]})`}
          />
          <Kv k="Class" v="Likely Pathogenic" tone="warn" />
          <Kv k="PhyloP" v="0.96" tone="ok" />
        </div>
        <div className="side-links">
          {VARIANT_LINKS.map((l) => (
            <a
              key={l.label}
              className="side-link"
              href={l.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              {l.label} ↗
            </a>
          ))}
        </div>
      </Section>

      <Section title="Transcript">
        <div className="kv-list">
          <Kv k="Gene" v={`${data.gene} · ${data.ensg}`} />
          <Kv k="Transcript" v={data.transcript} />
          <Kv
            k="Genomic"
            v={`${g.chrom}:${g.start.toLocaleString()}–${g.end.toLocaleString()}`}
          />
          <Kv k="Gene length" v={`${data.geneLength.toLocaleString()} bp`} />
          <Kv k="mRNA length" v={`${data.mrnaLength.toLocaleString()} bp`} />
          <Kv k="CDS" v={`c.1–c.${data.cdsLength} · ${data.cdsLength.toLocaleString()} bp`} />
          <Kv k="5′ UTR" v={`${data.utr5Length} bp (exons 1–2)`} />
          <Kv k="3′ UTR" v={`${data.utr3Length.toLocaleString()} bp (exon ${data.totalExons})`} />
          <Kv k="Protein" v={`${data.proteinLength} aa`} />
          <Kv
            k="Native strand"
            v={g.strand === '-' ? 'reverse (←)' : 'forward (→)'}
            tone="warn"
          />
        </div>

        {/* Modification #2: the exon table is a collapsible disclosure. */}
        <button
          type="button"
          className="side-disclosure"
          aria-expanded={exonTableOpen}
          aria-controls="side-exon-table"
          onClick={onToggleExonTable}
        >
          <span>Exons (click to view)</span>
          <span className="side-disclosure-meta">
            {data.totalExons} total · viewing exon {activeExon}
          </span>
          <svg
            className={`side-disclosure-chev${exonTableOpen ? ' open' : ''}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {exonTableOpen && (
          <div className="side-exon-table" id="side-exon-table">
            {data.exons.map((ex) => {
              const len = ex.cdsEnd - ex.cdsStart + 1
              const cls = [
                'side-exon-row',
                ex.num >= 3 && ex.num <= 5 ? 'in-window' : '',
                ex.num === activeExon ? 'current' : '',
              ]
                .filter(Boolean)
                .join(' ')
              return (
                <button
                  key={ex.num}
                  type="button"
                  className={cls}
                  title={`Exon ${ex.num} · ${len} bp · ${
                    data.exonVariantCount[ex.num] || 0
                  } ClinVar variants`}
                  onClick={() => onJumpToExon(ex.num)}
                >
                  <span className="ex-num">{ex.num}</span>
                  <span className="ex-range">
                    c.{ex.cdsStart}–{ex.cdsEnd}
                  </span>
                  <span className="ex-bp">{len} bp</span>
                  <span className="ex-var">{data.exonVariantCount[ex.num] || 0}</span>
                </button>
              )
            })}
          </div>
        )}
        <div className="side-source">
          Source: NCBI Entrez (gene/Gene_summary) · Ensembl REST (exon coords)
        </div>
      </Section>

      <Section title="Protein features">
        <div className="kv-list">
          <Kv k="Length" v={`${data.proteinLength} aa`} />
          <Kv
            k="Signal peptide"
            v={pf.signalPeptide ? `aa ${pf.signalPeptide.aaStart}–${pf.signalPeptide.aaEnd}` : 'none'}
            tone={pf.signalPeptide ? 'warn' : 'ok'}
          />
          <Kv
            k="Transmembrane"
            v={pf.transmembrane.length ? `${pf.transmembrane.length} segment(s)` : 'none'}
            tone={pf.transmembrane.length ? 'warn' : 'ok'}
          />
        </div>
        {pf.domains.length > 0 && (
          <>
            <div className="side-mini-h">Domains</div>
            {pf.domains.map((d) => (
              <FeatRow
                key={`${d.aaStart}-${d.aaEnd}-${d.label}`}
                rg={`aa ${d.aaStart}–${d.aaEnd}`}
                lb={d.label}
                rt={`${d.aaEnd - d.aaStart + 1} aa`}
              />
            ))}
          </>
        )}
        {pf.activeSites.length > 0 && (
          <>
            <div className="side-mini-h">Active sites</div>
            {pf.activeSites.map((s) => (
              <FeatRow key={`${s.aa}-${s.label}`} rg={`aa ${s.aa}`} lb={s.label} rt={s.residue} />
            ))}
          </>
        )}
        {pf.palmitoylation.length > 0 && (
          <>
            <div className="side-mini-h">Post-translational</div>
            {pf.palmitoylation.map((p) => (
              <FeatRow key={`${p.aa}-${p.label}`} rg={`aa ${p.aa}`} lb={p.label} rt={p.residue} />
            ))}
          </>
        )}
        <div className="side-source">Source: UniProt Q16518 · Proteins API</div>
      </Section>

      <Section
        title="Scratchpad"
        meta={
          scratch.length > 0 ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="count">
                {scratch.length} edit{scratch.length === 1 ? '' : 's'}
              </span>
              <button
                type="button"
                className="side-h-action"
                onClick={onResetAll}
              >
                Reset
              </button>
            </span>
          ) : undefined
        }
      >
        {selection && (
          <SelectionBlock
            selection={selection}
            onDel={onDelSelection}
            onReplace={onReplaceSelection}
            onClear={onClearSelection}
          />
        )}
        <div className="scratch-list">
          {scratch.length === 0 ? (
            <div className="scratch-empty">
              Left-click or drag in the canvas to select bases. Right-click a
              base to edit it (substitute / delete / insert). Predicted
              consequences land here.
            </div>
          ) : (
            scratch.map((e) => (
              <div className="scratch-row" key={e.idx}>
                <div className="top">
                  <span className="pos">
                    c.{e.cdsPos} {e.ref}&gt;{e.alt === '-' ? 'del' : e.alt}
                  </span>
                  <span className={`conseq ${e.conseq.kind}`}>{e.conseq.label}</span>
                </div>
                <div className="desc">{e.conseq.detail}</div>
              </div>
            ))
          )}
        </div>
      </Section>

      <Section title="AI note">
        <div className="side-info">
          <b>Why this variant matters.</b> Codon 87 sits in the strictly
          conserved core of the carotenoid-oxygenase domain (PhyloP 0.96). The
          Asp→Gly swap removes a charged residue from a helical patch that
          contacts the catalytic Fe²⁺. Two adjacent ClinVar entries (c.247
          V83I, c.277 R93C) are also pathogenic — this region is intolerant to
          substitution.
        </div>
      </Section>
    </>
  )
}

/** Tool context for the CRISPR designer — editing strategy, target window,
 *  and the (gated) AI-assist scaffolds. Mirrors the ViewerSide vocabulary. */
function CrisprSide({ data }: { data: GeneWindowData }) {
  const qv = data.queriedVariant
  const ex = data.exons.find(
    (e) => qv.cdsPos >= e.cdsStart && qv.cdsPos <= e.cdsEnd,
  )
  return (
    <>
      <Section title="Editing strategy">
        <div className="kv-list">
          <Kv k="Approach" v="HDR knock-in (ssODN)" />
          <Kv k="Nuclease" v="SpCas9 · NGG PAM" />
          <Kv k="Target" v={`${qv.hgvsC} (${qv.hgvsP})`} tone="warn" />
          <Kv k="Repair" v="ssODN · ±60 nt homology arms" />
        </div>
        <div className="side-info">
          <b>Goal.</b> Revert the pathogenic {qv.refBase}&gt;{qv.altBase} at{' '}
          {qv.hgvsC} with a silent PAM-blocking edit to prevent re-cutting of
          the corrected allele.
        </div>
      </Section>

      <Section title="Target window">
        <div className="kv-list">
          <Kv
            k="Region"
            v={ex ? `exon ${ex.num} · c.${ex.cdsStart}–${ex.cdsEnd}` : '—'}
          />
          <Kv k="PAM scan" v="both strands" />
          <Kv k="Search ± bp" v="10 (default)" />
        </div>
        <div className="side-source">
          Guides are scored against the design template returned with the
          result; whole-genome off-target lands with the engine (M-002D).
        </div>
      </Section>

      <Section title="AI assist">
        <div className="side-info">
          Guided design help arrives with the CRISPR engine (FE-6 / M-002D).
        </div>
        <div className="side-chips">
          <span className="side-chip">Pick the safest guide</span>
          <span className="side-chip">Explain off-target risk</span>
          <span className="side-chip">HDR design rationale</span>
        </div>
      </Section>
    </>
  )
}

/** Tool context for the Primer designer — assay strategy, target window,
 *  and the (gated) AI-assist scaffolds. Mirrors the CrisprSide vocabulary. */
function PrimerSide({ data }: { data: GeneWindowData }) {
  const qv = data.queriedVariant
  const ex = data.exons.find(
    (e) => qv.cdsPos >= e.cdsStart && qv.cdsPos <= e.cdsEnd,
  )
  return (
    <>
      <Section title="Assay strategy">
        <div className="kv-list">
          <Kv k="Approach" v="Sanger / qPCR amplicon" />
          <Kv k="Engine" v="Primer3 · local" />
          <Kv k="Target" v={`${qv.hgvsC} (${qv.hgvsP})`} tone="warn" />
          <Kv k="Specificity" v="in-template (UCSC isPcr opt-in)" />
        </div>
        <div className="side-info">
          <b>Goal.</b> Design a balanced primer pair whose amplicon spans{' '}
          {qv.hgvsC}, with matched Tm and a single specific product.
        </div>
      </Section>

      <Section title="Target window">
        <div className="kv-list">
          <Kv
            k="Region"
            v={ex ? `exon ${ex.num} · c.${ex.cdsStart}–${ex.cdsEnd}` : '—'}
          />
          <Kv k="Tm band" v="58–62 °C (default)" />
          <Kv k="Product" v="300–700 bp (default)" />
        </div>
        <div className="side-source">
          Pairs are screened against the resolved design template; whole-genome
          specificity needs the local UCSC isPcr provider (M-002C, gated).
        </div>
      </Section>

      <Section title="AI assist">
        <div className="side-info">
          Guided primer help arrives with the design engine (FE-6 / M-002C).
        </div>
        <div className="side-chips">
          <span className="side-chip">Pick the safest pair</span>
          <span className="side-chip">Explain specificity</span>
          <span className="side-chip">Redesign for qPCR</span>
        </div>
      </Section>
    </>
  )
}

export function SidePanel(props: SidePanelProps) {
  const { tool, collapsed, onToggleCollapsed } = props
  const meta = TOOL_META[tool]
  return (
    <aside className="side" id="side">
      <div className="side-collapse-row">
        <button
          type="button"
          className="side-collapse-btn"
          title={collapsed ? 'Expand context panel' : 'Collapse context panel'}
          aria-label={collapsed ? 'Expand context panel' : 'Collapse context panel'}
          onClick={onToggleCollapsed}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <polyline points={collapsed ? '15 18 9 12 15 6' : '9 18 15 12 9 6'} />
          </svg>
        </button>
      </div>

      {collapsed ? (
        <div className="side-collapsed-stub">
          <span className="vlabel">CONTEXT</span>
        </div>
      ) : tool === 'viewer' ? (
        <ViewerSide {...props} />
      ) : tool === 'primer' ? (
        <PrimerSide data={props.data} />
      ) : tool === 'crispr' ? (
        <CrisprSide data={props.data} />
      ) : (
        <Section title={meta.rail} meta={<span className="count">context</span>}>
          <div className="side-info">
            <b>{meta.title}</b> — {meta.sub}
          </div>
        </Section>
      )}
    </aside>
  )
}
