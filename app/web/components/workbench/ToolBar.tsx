'use client'
import type { WorkbenchTool } from '@/lib/backend'
import { TOOL_ORDER, TOOL_META } from './tools'
import { ToolIcon } from './ToolIcon'

interface ToolBarProps {
  active: WorkbenchTool
  onSelect: (tool: WorkbenchTool) => void
}

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
