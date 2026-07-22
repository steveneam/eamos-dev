'use client'

import { useCallback, useState } from 'react'
import { DesignTab } from './DesignTab'
import { OffTargetTab } from './OffTargetTab'
import { OutcomesTab } from './OutcomesTab'
import type { WorkbenchDesignContextV1 } from '@/lib/backend'
import type { WorkbenchDerivedResultV1 } from '@/lib/workbench/workspace'

export type CrisprSubTab = 'design' | 'offtargets' | 'outcomes'

/** A guide handed from Design to the Off-targets tab. A missing genomic locus
 * keeps enumeration disabled; template-relative offsets are never relabeled as
 * genomic coordinates. */
export interface ScreenSeed {
  guide: string
  pam: string
  strand?: '+' | '-'
  source: string
  contextDigest: string
  genomicLocus: { chromosome: string; position: number; strand: '+' | '-' } | null
}

interface CrisprPanelProps {
  gene: string
  cdna: string
  /** Fires when the sub-tab changes — lets the shell auto-collapse the viewer
   *  for the widest content (Off-targets). One-way nudge, not a lock. */
  onSubTabChange?: (tab: CrisprSubTab) => void
  designContext: WorkbenchDesignContextV1 | null
  restoredResultDigest?: string
  restoredDerivedResult?: WorkbenchDerivedResultV1
  onResultDigest?: (digest: string, summary: WorkbenchDerivedResultV1) => void
  executionBlockedReason: string | null
}

type SubTab = CrisprSubTab

const TAB_TITLE: Record<SubTab, string> = {
  design: 'Guide design & repair',
  offtargets: 'Off-target screening',
  outcomes: 'Editing outcomes',
}

const TAB_SUB: Record<SubTab, string> = {
  design: 'Local SpCas9 design surface / ssODN HDR template',
  offtargets: 'Enumerate → curate → screening primers for off-target validation',
  outcomes: 'Observed-only spectrum unless backend provides TIDE/Lindel data',
}

/**
 * CRISPR tool panel. Design is the local SpCas9 gRNA/HDR surface; Outcomes
 * stays observed-only until backend metadata proves real TIDE/Lindel data.
 */
export function CrisprPanel({
  gene,
  cdna,
  designContext,
  restoredResultDigest,
  restoredDerivedResult,
  onResultDigest,
  executionBlockedReason,
  onSubTabChange,
}: CrisprPanelProps) {
  const [tab, setTab] = useState<SubTab>('design')
  const [screenSeed, setScreenSeed] = useState<ScreenSeed | null>(null)
  const [resultDigest, setResultDigest] = useState<string | null>(null)
  const selectTab = (next: SubTab) => {
    setTab(next)
    onSubTabChange?.(next)
  }
  // Design hands a guide to Off-targets: stash the seed, then jump tabs (which
  // also auto-collapses the viewer for the wider screening table).
  const handleScreenGuide = (seed: ScreenSeed) => {
    setScreenSeed(seed)
    selectTab('offtargets')
  }
  const handleSeedConsumed = useCallback(() => setScreenSeed(null), [])
  const recordDigest = useCallback((digest: string) => {
    setResultDigest(digest)
    onResultDigest?.(digest, {
      schema_version: 'workbench_derived_result.v1',
      tool: 'crispr',
      context_digest: designContext?.context_digest ?? null,
      result_digest: digest,
      recorded_at: new Date().toISOString(),
      title: `${TAB_TITLE[tab]} completed`,
      metrics: {
        subtool: tab,
        provider_proof_required: true,
      },
    })
  }, [designContext?.context_digest, onResultDigest, tab])
  const stale = Boolean(
    resultDigest && (!designContext || resultDigest !== designContext.context_digest),
  )

  return (
    <div className="crispr-panel">
      <div className="tool-panel-head">
        <div>
          <h2 className="tool-panel-title">{TAB_TITLE[tab]}</h2>
          <span className="tool-panel-sub">{TAB_SUB[tab]}</span>
        </div>
        <div className="seg" role="tablist" aria-label="CRISPR sub-tool">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'design'}
            className={tab === 'design' ? 'active' : ''}
            onClick={() => selectTab('design')}
            title="Design candidate guide RNAs for this target (step 1)"
          >
            Design
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'offtargets'}
            className={tab === 'offtargets' ? 'active' : ''}
            onClick={() => selectTab('offtargets')}
            title="Screen a guide for genome-wide off-target sites (step 2)"
          >
            Off-targets
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'outcomes'}
            className={tab === 'outcomes' ? 'active' : ''}
            onClick={() => selectTab('outcomes')}
            title="Confirm edit outcomes from sequencing traces (step 3)"
          >
            Outcomes
          </button>
        </div>
      </div>

      <div className="workbench-context-binding" role="note">
        {designContext
          ? `Bound to ${designContext.selection.chrom}:${designContext.selection.genomic_start.toLocaleString('en-US')}-${designContext.selection.genomic_end.toLocaleString('en-US')} · ${designContext.selection.sequence_basis} · revision ${designContext.selection.edit_revision}`
          : 'Exact source-backed context is unresolved. CRISPR requests are disabled.'}
      </div>
      {stale ? (
        <div className="workbench-stale" role="status">
          Previous CRISPR results are retained but stale because the selection or edit revision changed.
        </div>
      ) : null}
      {!resultDigest && restoredResultDigest && restoredDerivedResult ? (
        <div className="workbench-context-binding" role="note">
          Retained derived summary: {restoredDerivedResult.title} · result {restoredResultDigest.slice(0, 10)}. Guide, donor, and trace inputs are not persisted.
        </div>
      ) : null}
      {!resultDigest && restoredResultDigest && !restoredDerivedResult ? (
        <div className="workbench-context-binding" role="note">
          This tab retained only prior CRISPR result identity ({restoredResultDigest.slice(0, 10)}). Rerun to restore details.
        </div>
      ) : null}
      {executionBlockedReason ? (
        <div className="workbench-stale" role="alert">{executionBlockedReason}</div>
      ) : null}

      {tab === 'design' ? (
        <DesignTab
          gene={gene}
          cdna={cdna}
          designContext={designContext}
          executionBlockedReason={executionBlockedReason}
          onResultDigest={recordDigest}
          onScreenGuide={handleScreenGuide}
        />
      ) : tab === 'offtargets' ? (
        <OffTargetTab
          gene={gene}
          cdna={cdna}
          designContext={designContext}
          executionBlockedReason={executionBlockedReason}
          onResultDigest={recordDigest}
          seed={screenSeed}
          onSeedConsumed={handleSeedConsumed}
        />
      ) : (
        <OutcomesTab designContext={designContext} onResultDigest={recordDigest} />
      )}
    </div>
  )
}
