import { useState } from 'react'
import { DesignTab } from './DesignTab'
import { OutcomesTab } from './OutcomesTab'

interface CrisprPanelProps {
  gene: string
  cdna: string
}

type SubTab = 'design' | 'outcomes'

/**
 * CRISPR tool panel. Two sub-tabs inside the single CRISPR rail entry
 * (locked decision, plans/crispr-integration.md §2.4): `Design` =
 * Blueprint-1 gRNA design (live now, mock-first against /api/v1/crispr);
 * `Outcomes` = Blueprint-2 post-edit TIDE analytics scaffold (mock-first
 * until the Codex §7 backend lands). The rail stays at 5 tools.
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
              ? 'PAM scan · Hsu off-target · ssODN HDR template'
              : 'TIDE Sanger deconvolution · indel spectrum'}
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
