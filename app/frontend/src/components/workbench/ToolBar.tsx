import type { WorkbenchTool } from '@/lib/backend'
import { TOOL_ORDER, TOOL_META, ToolIcon } from './tools'

interface ToolBarProps {
  active: WorkbenchTool
  onSelect: (tool: WorkbenchTool) => void
}

/** Modification #3: horizontal segmented tool selector, top-right of the
 *  canvas header. Replaces the old left vertical `ToolRail` — reclaims the
 *  64 px rail column for the sequence viewer. */
export function ToolBar({ active, onSelect }: ToolBarProps) {
  return (
    <div className="toolbar-seg" role="group" aria-label="Workbench tools">
      {TOOL_ORDER.map((tool) => (
        <button
          key={tool}
          type="button"
          className={tool === active ? 'toolbar-seg-btn active' : 'toolbar-seg-btn'}
          data-tool={tool}
          title={TOOL_META[tool].title}
          aria-pressed={tool === active}
          onClick={() => onSelect(tool)}
        >
          <ToolIcon tool={tool} />
          <span>{TOOL_META[tool].rail}</span>
        </button>
      ))}
    </div>
  )
}
