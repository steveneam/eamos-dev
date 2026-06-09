'use client'
import { useState, type ReactNode } from 'react'
import {
  IconChevron,
  IconFlask,
  IconGene,
  IconProtein,
  IconRename,
  IconScissors,
  IconScope,
  IconSparkle,
  IconWindow,
} from '@/components/icons/Icon'
import type { WorkbenchTool } from '@/lib/backend'
import { aaThree } from '@/lib/workbench/codon-table'
import { classLabel, type ClinvarVariant, type GeneWindowData } from '@/lib/workbench/gene-window'
import { TOOL_META } from './tools'
import type { ScratchEntry } from './viewer/SequenceViewerV2'
import type { SelectionSummary } from './viewer/viewer-types'

const VARIANT_LINKS = [
  { label: 'ClinVar', href: 'https://www.ncbi.nlm.nih.gov/clinvar/variation/99473/' },
  { label: 'gnomAD', href: 'https://gnomad.broadinstitute.org' },
]

interface SidePanelProps {
  tool: WorkbenchTool
  data: GeneWindowData
  scratch: ScratchEntry[]
  selection: SelectionSummary | null
  selectedClinvar: ClinvarVariant | null
  exonTableOpen: boolean
  activeExon: number
  onToggleExonTable: () => void
  onResetAll: () => void
  onJumpToExon: (n: number) => void
  onDelSelection: () => void
  onReplaceSelection: (seq: string) => void
  onClearSelection: () => void
  onClearClinvar: () => void
}

function Kv({ k, v, tone }: { k: string; v: string; tone?: 'warn' | 'ok' }) {
  return (
    <div className="kv-row">
      <div className="k">{k}</div>
      <div className={tone ? `v ${tone}` : 'v'}>{v}</div>
    </div>
  )
}

/** Collapsible side-panel section. Header row mirrors the viewer's
 *  `.sv-section-head` chevron pattern so the whole workbench reads the
 *  same way. Local-only open state — close one without affecting siblings.
 *  Use `tone="scratch"` for the yellow Scratchpad surface. */
function CollapsibleSection({
  title,
  icon,
  meta,
  children,
  defaultOpen = true,
  tone,
  id,
}: {
  title: string
  /** Leading monochrome glyph — same airy icon-led grammar as <WorkRailSection>. */
  icon?: ReactNode
  meta?: ReactNode
  children: ReactNode
  defaultOpen?: boolean
  tone?: 'scratch'
  id?: string
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div
      className={`side-section${tone === 'scratch' ? ' is-scratchpad' : ''}${open ? '' : ' is-collapsed'}`}
      id={id}
    >
      <button
        type="button"
        className="side-section-head"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {icon ? <span className="side-section-icon" aria-hidden="true">{icon}</span> : null}
        <span className="side-section-title">{title}</span>
        {meta ? <span className="side-section-meta">{meta}</span> : null}
        <span className="side-section-chev" aria-hidden="true">
          <IconChevron size={12} />
        </span>
      </button>
      {open && <div className="side-section-body">{children}</div>}
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
        <div className="scratch-sel-esc">
          Press <b>Esc</b> or click empty canvas to clear.
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
      <div className="scratch-sel-esc">
        Press <b>Esc</b> or click empty canvas to clear.
      </div>
    </div>
  )
}

/** Info card for the ClinVar dot the user clicked in the viewer. Mirrors the
 *  `.scratch-sel` card shape; the classification chip reuses the lollipop
 *  colour ramp (`.scratch-cv-cls.<cls>`). */
function ClinvarFocusCard({
  variant,
  onClear,
}: {
  variant: ClinvarVariant
  onClear: () => void
}) {
  const numericId = variant.cv.replace(/\D/g, '').replace(/^0+/, '')
  const href = numericId
    ? `https://www.ncbi.nlm.nih.gov/clinvar/variation/${numericId}/`
    : null
  return (
    <div className="scratch-cv">
      <div className="scratch-cv-head">
        <span className="lbl">ClinVar variant</span>
        <span className={`scratch-cv-cls ${variant.cls}`}>{classLabel(variant.cls)}</span>
      </div>
      <div className="scratch-cv-hgvs">{variant.hgvsC}</div>
      {variant.hgvsP ? <div className="scratch-cv-hgvs sub">{variant.hgvsP}</div> : null}
      <div className="scratch-cv-actions">
        {href ? (
          <a
            className="scratch-cv-link"
            href={href}
            target="_blank"
            rel="noopener noreferrer"
          >
            {variant.cv} ↗
          </a>
        ) : null}
        <button type="button" className="scratch-sel-btn ghost" onClick={onClear}>
          Clear
        </button>
      </div>
    </div>
  )
}

type ScratchTab = 'log' | 'notes' | 'ask'

/** Scratchpad is the user's workbench — a log of edits + free-form notes +
 *  variant-aware chat. Sits at the top of the side panel on a warm yellow
 *  surface to read as "your workspace" against the cooler neutral
 *  evidence sections below. */
function ScratchpadSection({
  scratch,
  selection,
  selectedClinvar,
  onResetAll,
  onDelSelection,
  onReplaceSelection,
  onClearSelection,
  onClearClinvar,
}: {
  scratch: ScratchEntry[]
  selection: SelectionSummary | null
  selectedClinvar: ClinvarVariant | null
  onResetAll: () => void
  onDelSelection: () => void
  onReplaceSelection: (seq: string) => void
  onClearSelection: () => void
  onClearClinvar: () => void
}) {
  const [tab, setTab] = useState<ScratchTab>('log')
  const [notes, setNotes] = useState('')

  const meta =
    tab === 'log' && scratch.length > 0 ? (
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="count">
          {scratch.length} edit{scratch.length === 1 ? '' : 's'}
        </span>
        <button
          type="button"
          className="side-h-action"
          onClick={(e) => {
            e.stopPropagation()
            onResetAll()
          }}
        >
          Reset
        </button>
      </span>
    ) : undefined

  return (
    <CollapsibleSection title="Scratchpad" icon={<IconRename size={14} />} meta={meta} tone="scratch" defaultOpen>
      <div className="scratch-tabs" role="tablist" aria-label="Scratchpad mode">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'log'}
          className={`scratch-tab${tab === 'log' ? ' active' : ''}`}
          onClick={() => setTab('log')}
        >
          Log
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'notes'}
          className={`scratch-tab${tab === 'notes' ? ' active' : ''}`}
          onClick={() => setTab('notes')}
        >
          Notes
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'ask'}
          className={`scratch-tab${tab === 'ask' ? ' active' : ''}`}
          onClick={() => setTab('ask')}
        >
          Ask Eamos
        </button>
      </div>

      {tab === 'log' && (
        <>
          {selectedClinvar && (
            <ClinvarFocusCard variant={selectedClinvar} onClear={onClearClinvar} />
          )}
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
        </>
      )}

      {tab === 'notes' && (
        <div className="scratch-notes">
          <textarea
            className="scratch-notes-area"
            placeholder="Jot working notes about this variant — questions for review, things to follow up on, design rationale…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            spellCheck
            rows={8}
            aria-label="Notes"
          />
          <div className="scratch-notes-hint">
            Notes live in this tab for the session. Persistent saving lands with
            the account workspace.
          </div>
        </div>
      )}

      {tab === 'ask' && (
        <div className="scratch-ask">
          <div className="scratch-ask-badge">COMING SOON</div>
          <p className="scratch-ask-copy">
            Variant-aware chat. Ask follow-up questions about this gene, this
            variant, the literature, the call cards, or what to do next — Eamos
            answers with cited sources from the report.
          </p>
          <div className="scratch-ask-input-row">
            <input
              type="text"
              className="scratch-ask-input"
              placeholder="Ask about this variant…"
              disabled
              aria-label="Ask Eamos (coming soon)"
            />
            <button type="button" className="scratch-ask-btn" disabled aria-label="Send (coming soon)">
              →
            </button>
          </div>
        </div>
      )}
    </CollapsibleSection>
  )
}

function ViewerSide({
  data,
  scratch,
  selection,
  selectedClinvar,
  exonTableOpen,
  activeExon,
  onToggleExonTable,
  onResetAll,
  onJumpToExon,
  onDelSelection,
  onReplaceSelection,
  onClearSelection,
  onClearClinvar,
}: Omit<SidePanelProps, 'tool'>) {
  const qv = data.queriedVariant
  const g = data.genomicCoords
  const pf = data.proteinFeatures
  const product = data.proteinProduct
  const proteinLengthLabel =
    product?.truncatesProtein && product.referenceProteinLength != null
      ? `${product.effectiveProteinLength ?? data.proteinLength} / ${product.referenceProteinLength} aa`
      : `${data.proteinLength} aa`

  return (
    <>
      {/* Scratchpad first — your workspace lives above the evidence. */}
      <ScratchpadSection
        scratch={scratch}
        selection={selection}
        selectedClinvar={selectedClinvar}
        onResetAll={onResetAll}
        onDelSelection={onDelSelection}
        onReplaceSelection={onReplaceSelection}
        onClearSelection={onClearSelection}
        onClearClinvar={onClearClinvar}
      />

      <CollapsibleSection title="Active variant" icon={<IconScope size={14} />}>
        <div className="kv-list">
          <Kv k="HGVS (c.)" v={qv.hgvsC} tone="warn" />
          <Kv k="HGVS (p.)" v={qv.hgvsP} tone="warn" />
          <Kv
            k="Codon"
            v={`${qv.codonNumber} (${aaThree[qv.aaRef] ?? qv.aaRef} → ${aaThree[qv.aaAlt] ?? qv.aaAlt})`}
          />
          {product && (
            <Kv
              k="Product"
              v={product.label}
              tone={product.truncatesProtein ? 'warn' : undefined}
            />
          )}
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
      </CollapsibleSection>

      <CollapsibleSection title="Transcript" icon={<IconGene size={14} />}>
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
          <Kv
            k="Protein"
            v={proteinLengthLabel}
            tone={product?.truncatesProtein ? 'warn' : undefined}
          />
          <Kv
            k="Native strand"
            v={g.strand === '-' ? 'reverse (←)' : 'forward (→)'}
            tone="warn"
          />
        </div>

        {/* Nested disclosure styled to match the section headers above. */}
        <button
          type="button"
          className="side-nested-head"
          aria-expanded={exonTableOpen}
          aria-controls="side-exon-table"
          onClick={onToggleExonTable}
        >
          <span className="side-nested-chev" aria-hidden="true">
            <IconChevron size={12} />
          </span>
          <span className="side-nested-title">Exons</span>
          <span className="side-nested-meta">
            {data.totalExons} total · viewing exon {activeExon}
          </span>
        </button>
        {exonTableOpen && (
          <div className="side-exon-table" id="side-exon-table">
            {data.exons.map((ex) => {
              const len = ex.cdsEnd - ex.cdsStart + 1
              const cls = [
                'side-exon-row',
                ex.num >= 3 && ex.num <= 5 ? 'in-window' : '',
                ex.num === activeExon ? 'current' : '',
                ex.proteinState === 'contains_variant' ? 'contains-variant' : '',
                ex.proteinState === 'downstream_truncated' ? 'downstream-truncated' : '',
              ]
                .filter(Boolean)
                .join(' ')
              return (
                <button
                  key={ex.num}
                  type="button"
                  className={cls}
                  title={[
                    `Exon ${ex.num} · ${len} bp · ${
                      data.exonVariantCount[ex.num] || 0
                    } ClinVar variants`,
                    ex.proteinState === 'contains_variant' ? 'variant-applied product affected' : '',
                    ex.proteinState === 'downstream_truncated'
                      ? `${ex.lostCdsBases ?? 0} CDS bp lost from product`
                      : '',
                  ]
                    .filter(Boolean)
                    .join(' · ')}
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
      </CollapsibleSection>

      <CollapsibleSection title="Protein features" icon={<IconProtein size={14} />}>
        <div className="kv-list">
          <Kv
            k="Length"
            v={proteinLengthLabel}
            tone={product?.truncatesProtein ? 'warn' : undefined}
          />
          {product && (
            <Kv
              k="Variant product"
              v={product.label}
              tone={product.truncatesProtein ? 'warn' : undefined}
            />
          )}
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
      </CollapsibleSection>

      <CollapsibleSection title="AI note" icon={<IconSparkle size={14} />} defaultOpen={false}>
        <div className="side-info">
          <b>Why this variant matters.</b> Codon 87 sits in the strictly
          conserved core of the carotenoid-oxygenase domain (PhyloP 0.96). The
          Asp→Gly swap removes a charged residue from a helical patch that
          contacts the catalytic Fe²⁺. Two adjacent ClinVar entries (c.247
          V83I, c.277 R93C) are also pathogenic — this region is intolerant to
          substitution.
        </div>
      </CollapsibleSection>
    </>
  )
}

function CrisprSide({ data }: { data: GeneWindowData }) {
  const qv = data.queriedVariant
  const ex = data.exons.find(
    (e) => qv.cdsPos >= e.cdsStart && qv.cdsPos <= e.cdsEnd,
  )
  return (
    <>
      <CollapsibleSection title="Editing strategy" icon={<IconScissors size={14} />}>
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
      </CollapsibleSection>

      <CollapsibleSection title="Target window" icon={<IconWindow size={14} />}>
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
      </CollapsibleSection>

      <CollapsibleSection title="AI assist" icon={<IconSparkle size={14} />}>
        <div className="side-info">
          Guided design help arrives with the CRISPR engine (FE-6 / M-002D).
        </div>
        <div className="side-chips">
          <span className="side-chip">Pick the safest guide</span>
          <span className="side-chip">Explain off-target risk</span>
          <span className="side-chip">HDR design rationale</span>
        </div>
      </CollapsibleSection>
    </>
  )
}

function PrimerSide({ data }: { data: GeneWindowData }) {
  const qv = data.queriedVariant
  const ex = data.exons.find(
    (e) => qv.cdsPos >= e.cdsStart && qv.cdsPos <= e.cdsEnd,
  )
  return (
    <>
      <CollapsibleSection title="Assay strategy" icon={<IconFlask size={14} />}>
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
      </CollapsibleSection>

      <CollapsibleSection title="Target window" icon={<IconWindow size={14} />}>
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
      </CollapsibleSection>

      <CollapsibleSection title="AI assist" icon={<IconSparkle size={14} />}>
        <div className="side-info">
          Guided primer help arrives with the design engine (FE-6 / M-002C).
        </div>
        <div className="side-chips">
          <span className="side-chip">Pick the safest pair</span>
          <span className="side-chip">Explain specificity</span>
          <span className="side-chip">Redesign for qPCR</span>
        </div>
      </CollapsibleSection>
    </>
  )
}

export function SidePanel(props: SidePanelProps) {
  const { tool } = props
  const meta = TOOL_META[tool]
  return (
    <aside className="side" id="side">
      {tool === 'viewer' ? (
        <ViewerSide {...props} />
      ) : tool === 'primer' ? (
        <PrimerSide data={props.data} />
      ) : tool === 'crispr' ? (
        <CrisprSide data={props.data} />
      ) : (
        <CollapsibleSection title={meta.rail} icon={<IconScope size={14} />} meta={<span className="count">context</span>}>
          <div className="side-info">
            <b>{meta.title}</b> — {meta.sub}
          </div>
        </CollapsibleSection>
      )}
    </aside>
  )
}
