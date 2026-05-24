import { useState } from 'react'
import { DesignTab } from './DesignTab'
import { OutcomesTab } from './OutcomesTab'

interface CrisprPanelProps {
  gene: string
  cdna: string
}

type SubTab = 'design' | 'outcomes'

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
          <h2 className="tool-panel-title">
            {tab === 'design' ? 'Guide design & repair' : 'Editing outcomes'}
          </h2>
          <span className="tool-panel-sub">
            {tab === 'design'
              ? 'Local SpCas9 design surface / ssODN HDR template'
              : 'Observed-only spectrum unless backend provides TIDE/Lindel data'}
          </span>
        </div>
        <div className="seg" role="tablist" aria-label="CRISPR sub-tool">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'design'}
            className={tab === 'design' ? 'active' : ''}
            onClick={() => setTab('design')}
          >
            Design
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'outcomes'}
            className={tab === 'outcomes' ? 'active' : ''}
            onClick={() => setTab('outcomes')}
          >
            Outcomes
          </button>
        </div>
      </div>

      {tab === 'design' ? (
        <DesignTab gene={gene} cdna={cdna} />
      ) : (
        <OutcomesTab />
      )}
    </div>
  )
}
