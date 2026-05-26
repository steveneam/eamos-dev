'use client'
import type { WorkbenchTool } from '@/lib/backend'
import { ToolBar } from './ToolBar'

interface ContextStripProps {
  gene: string
  variant: string
  tool: WorkbenchTool
  onSelectTool: (tool: WorkbenchTool) => void
}

// Minimal context — gene + variant only. The full transcript / coordinate /
// genome-build metrics live in the right-hand workspace panel; the strip
// stays a clean wayfinder.
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
