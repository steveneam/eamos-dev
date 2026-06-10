'use client'

import { useCallback, useState } from 'react'
import { DesignTab } from './DesignTab'
import { OffTargetTab } from './OffTargetTab'
import { OutcomesTab } from './OutcomesTab'

export type CrisprSubTab = 'design' | 'offtargets' | 'outcomes'

/** A guide handed from Design to the Off-targets tab via the "Screen ↗" bridge.
 *  Carries only what the off-target form needs to pre-fill; the genomic locus is
 *  deliberately left out (Design positions are template-relative, not genomic). */
export interface ScreenSeed {
  guide: string
  pam: string
  strand?: '+' | '-'
  source: string
}

interface CrisprPanelProps {
  gene: string
  cdna: string
  /** Fires when the sub-tab changes — lets the shell auto-collapse the viewer
   *  for the widest content (Off-targets). One-way nudge, not a lock. */
  onSubTabChange?: (tab: CrisprSubTab) => void
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
export function CrisprPanel({ gene, cdna, onSubTabChange }: CrisprPanelProps) {
  const [tab, setTab] = useState<SubTab>('design')
  const [screenSeed, setScreenSeed] = useState<ScreenSeed | null>(null)
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

      {tab === 'design' ? (
        <DesignTab gene={gene} cdna={cdna} onScreenGuide={handleScreenGuide} />
      ) : tab === 'offtargets' ? (
        <OffTargetTab
          gene={gene}
          cdna={cdna}
          seed={screenSeed}
          onSeedConsumed={handleSeedConsumed}
        />
      ) : (
        <OutcomesTab />
      )}
    </div>
  )
}
