import { useState } from 'react'
import { DesignTab } from './DesignTab'
import { OutcomesTab } from './OutcomesTab'

interface CrisprPanelProps {
  gene: string
  cdna: string
}

type SubTab = 'design' | 'outcomes'

/**
 * CRISPR tool panel. Design is the current gRNA/HDR fixture workflow;
 * Outcomes is the post-edit TIDE-shaped scaffold.
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
              ? 'Fixture scores / crisprScore plan / ssODN HDR template'
              : 'TIDE scaffold / observed indel spectrum'}
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
