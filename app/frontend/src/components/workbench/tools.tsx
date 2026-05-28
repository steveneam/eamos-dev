import type { WorkbenchTool } from '@/lib/backend'

export const TOOL_ORDER: WorkbenchTool[] = ['viewer', 'primer', 'crispr', 'align', 'compare']

interface ToolMeta {
  /** Rail label (short) */
  rail: string
  /** Canvas-header title */
  title: string
  /** Canvas-header subtitle */
  sub: string
  /** Whether the track-toggle group is shown for this tool */
  tracks: boolean
}

export const TOOL_META: Record<WorkbenchTool, ToolMeta> = {
  viewer: {
    rail: 'Sequence',
    title: 'Sequence viewer',
    sub: 'RPE65 (ENSG00000116745) · 21,139 bp · exon 4 around c.260',
    tracks: true,
  },
  primer: {
    rail: 'Primer',
    title: 'Primer designer',
    sub: 'Primer3 engine · Sanger / qPCR / Amplicon / ARMS modes',
    tracks: true,
  },
  crispr: {
    rail: 'CRISPR',
    title: 'CRISPR designer',
    sub: 'CRISPOR-style scoring · gRNA + ssODN repair template',
    tracks: true,
  },
  align: {
    rail: 'Align',
    title: 'Sequence alignment',
    sub: 'Pairwise alignment · paste / FASTA / AB1 chromatogram',
    tracks: false,
  },
  compare: {
    rail: 'Compare',
    title: 'Variant comparator',
    sub: 'Side-by-side comparison of 2–3 variants in this gene',
    tracks: false,
  },
}

/** Viewer collapses (canvas replaced) for alignment + comparator. */
export function viewerCollapsed(tool: WorkbenchTool): boolean {
  return tool === 'align' || tool === 'compare'
}
