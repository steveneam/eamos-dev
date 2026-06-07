'use client'
import type { WorkbenchTool } from '@/lib/backend'
import { ToolBar } from './ToolBar'

interface ContextStripProps {
  gene: string
  variant: string
  tool: WorkbenchTool
  onSelectTool: (tool: WorkbenchTool) => void
}

// The wayfinder strip directly under the shared nav: the active gene + variant
// on the left, the tool switcher (Sequence · Primer · CRISPR · Align) filling
// the space on the right — sitting right below the Report/Workbench/Batch
// toggle. Transcript / coordinate / build metrics stay in the left rail.
export function ContextStrip({ gene, variant, tool, onSelectTool }: ContextStripProps) {
  return (
    <div className="ctx-wrap">
      <div className="wrap-wide ctx">
        <div className="ctx-left">
          <span className="ctx-gene">{gene}</span>
          <span className="ctx-sep">·</span>
          <span className="ctx-var">{variant}</span>
        </div>
        <div className="ctx-right">
          <ToolBar active={tool} onSelect={onSelectTool} />
        </div>
      </div>
    </div>
  )
}
