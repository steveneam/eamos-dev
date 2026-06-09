'use client'

import { useState } from 'react'
import { DesignTab } from './DesignTab'
import { OffTargetTab } from './OffTargetTab'
import { OutcomesTab } from './OutcomesTab'

interface CrisprPanelProps {
  gene: string
  cdna: string
}

type SubTab = 'design' | 'offtargets' | 'outcomes'

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
export function CrisprPanel({ gene, cdna }: CrisprPanelProps) {
  const [tab, setTab] = useState<SubTab>('design')

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
            onClick={() => setTab('design')}
            title="Design candidate guide RNAs for this target (step 1)"
          >
            Design
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'offtargets'}
            className={tab === 'offtargets' ? 'active' : ''}
            onClick={() => setTab('offtargets')}
            title="Screen a guide for genome-wide off-target sites (step 2)"
          >
            Off-targets
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'outcomes'}
            className={tab === 'outcomes' ? 'active' : ''}
            onClick={() => setTab('outcomes')}
            title="Confirm edit outcomes from sequencing traces (step 3)"
          >
            Outcomes
          </button>
        </div>
      </div>

      {tab === 'design' ? (
        <DesignTab gene={gene} cdna={cdna} />
      ) : tab === 'offtargets' ? (
        <OffTargetTab gene={gene} cdna={cdna} />
      ) : (
        <OutcomesTab />
      )}
    </div>
  )
}
