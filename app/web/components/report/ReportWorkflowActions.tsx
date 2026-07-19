'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { buildWorkbenchHrefV1, type LookupResponse, type WorkflowActiveToolV1 } from '@/lib/backend'
import {
  canonicalVariantFromReport,
  sendCanonicalVariantToBatch,
  stashPaperTarget,
} from '@/lib/report-workflow'

const DESIGN_TOOLS: Array<{ tool: WorkflowActiveToolV1; label: string }> = [
  { tool: 'primer', label: 'Primer' },
  { tool: 'crispr', label: 'CRISPR' },
  { tool: 'align', label: 'Align' },
]

export function ReportWorkflowActions({ data }: { data: LookupResponse }) {
  const router = useRouter()
  const variant = canonicalVariantFromReport(data)
  if (!variant) return null
  const molecularReady = variant.resolution_status === 'resolved'

  const openPaper = () => {
    stashPaperTarget(variant)
    router.push('/paper')
  }

  const openBatch = () => {
    sendCanonicalVariantToBatch(variant, 'Variant report')
    router.push('/compare')
  }

  return (
    <details className="report-workflow-menu">
      <summary className="v-tool" aria-label="Continue this variant in another workflow">Continue</summary>
      <div className="report-workflow-popover">
        <span className="report-workflow-label">Continue with this variant</span>
        <Link href={buildWorkbenchHrefV1(variant, { tool: 'viewer' })}>Workbench</Link>
        <button type="button" onClick={openPaper}>Find in papers</button>
        <button type="button" onClick={openBatch}>Add to Batch</button>
        {DESIGN_TOOLS.map(({ tool, label }) =>
          molecularReady ? (
            <Link key={tool} href={buildWorkbenchHrefV1(variant, { tool })}>{label}</Link>
          ) : (
            <button
              type="button"
              key={tool}
              disabled
              title="A resolved transcript and GRCh38 variant are required"
            >
              {label}
            </button>
          ),
        )}
        {!molecularReady && (
          <p>Primer, CRISPR, and Align require a resolved transcript and GRCh38 identity.</p>
        )}
      </div>
      <style>{`
        .report-workflow-menu { position: relative; }
        .report-workflow-menu > summary { list-style: none; min-height: 44px; display: inline-flex; align-items: center; cursor: pointer; }
        .report-workflow-menu > summary::-webkit-details-marker { display: none; }
        .report-workflow-popover { position: absolute; z-index: 30; top: calc(100% + 7px); right: 0; width: min(280px, calc(100vw - 32px)); display: grid; grid-template-columns: 1fr 1fr; gap: 5px; padding: 10px; background: var(--bg); border: 0.5px solid var(--line-2); border-radius: 10px; box-shadow: var(--elev-3); }
        .report-workflow-label { grid-column: 1 / -1; padding: 2px 3px 5px; color: var(--ink-4); font-size: 10px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }
        .report-workflow-popover a, .report-workflow-popover button { min-height: 44px; display: inline-flex; align-items: center; justify-content: center; padding: 7px 9px; border: 0.5px solid var(--line); border-radius: 7px; background: var(--bg-soft); color: var(--ink-2); font: 600 11px var(--body); text-decoration: none; cursor: pointer; }
        .report-workflow-popover a:hover, .report-workflow-popover button:hover:not(:disabled) { background: var(--teal-tint); border-color: var(--teal-bdr); color: var(--teal-deep); }
        .report-workflow-popover a:focus-visible, .report-workflow-popover button:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }
        .report-workflow-popover button:disabled { color: var(--ink-5); cursor: not-allowed; }
        .report-workflow-popover p { grid-column: 1 / -1; margin: 3px; color: var(--ink-4); font-size: 10.5px; line-height: 1.4; }
        @media (max-width: 480px) {
          .report-workflow-popover { position: fixed; top: auto; right: 16px; bottom: 16px; left: 16px; width: auto; }
        }
      `}</style>
    </details>
  )
}
