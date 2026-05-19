import type { WorkbenchTool } from '@/lib/backend'
import { ToolBar } from './ToolBar'

interface ContextStripProps {
  gene: string
  variant: string
  sub: string
  tool: WorkbenchTool
  onSelectTool: (tool: WorkbenchTool) => void
}

/** FE-5.6 item 1: the strip's right cluster (classification badge + external
 *  links) is gone — classification lives in the side panel's Active variant
 *  card, the ClinVar/gnomAD links moved there too, and this slot now hosts the
 *  tool selector (moved out of the canvas header so it sits above the fold). */
export function ContextStrip({ gene, variant, sub, tool, onSelectTool }: ContextStripProps) {
  return (
    <div className="ctx-wrap">
      <div className="wrap-wide ctx">
        <div className="ctx-left">
          <span className="ctx-gene">{gene}</span>
          <span className="ctx-sep">·</span>
          <span className="ctx-var">{variant}</span>
          <span className="ctx-sub">{sub}</span>
        </div>
        <div className="ctx-right">
          <ToolBar active={tool} onSelect={onSelectTool} />
        </div>
      </div>
    </div>
  )
}
