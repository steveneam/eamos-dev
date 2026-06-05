'use client'
import type { WorkbenchTool } from '@/lib/backend'

interface ContextStripProps {
  gene: string
  variant: string
  tool: WorkbenchTool
  onSelectTool: (tool: WorkbenchTool) => void
}

// Minimal context — gene + variant only. The full transcript / coordinate /
// genome-build metrics live in the left rail; the tool switcher has also
// moved into the rail (Phase 2). The strip is a clean wayfinder only.
export function ContextStrip({ gene, variant }: ContextStripProps) {
  return (
    <div className="ctx-wrap">
      <div className="wrap-wide ctx">
        <div className="ctx-left">
          <span className="ctx-gene">{gene}</span>
          <span className="ctx-sep">·</span>
          <span className="ctx-var">{variant}</span>
        </div>
      </div>
    </div>
  )
}
