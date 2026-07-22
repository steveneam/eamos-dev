'use client'

import { useState, type CSSProperties } from 'react'
import Link from 'next/link'
import { openAuthMenu } from '@/components/auth/AuthMenu'
import { IconCheck } from '@/components/icons/Icon'
import type { BatchPage, BatchResult, WorkflowRunV1 } from '@/lib/backend'
import { BatchTable, rowFromResult } from './BatchTable'
import {
  isBatchIssue,
  issueCopy,
  type BatchProgress,
  type RunStatus,
} from './batchRunModel'

export function RecentBatchRuns({
  signedIn,
  state,
  currentRunId,
  onOpen,
  onCancel,
  onDelete,
}: {
  signedIn: boolean
  state: { runs: WorkflowRunV1[]; total: number | null; error: boolean } | null
  currentRunId: string | null
  onOpen: (runId: string) => void
  onCancel: (runId: string) => Promise<void>
  onDelete: (runId: string) => Promise<void>
}) {
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  if (!signedIn) return null
  if (!state) return <p className="mb-3" role="status" style={{ color: 'var(--ink-4)', fontSize: 11.5 }}>Loading saved Batch runs…</p>
  return (
    <details className="mb-3" style={{ border: '0.5px solid var(--line)', borderRadius: 10, background: 'var(--bg)' }}>
      <summary style={{ cursor: 'pointer', padding: '9px 11px', color: 'var(--ink-3)', fontSize: 11.5, fontWeight: 650 }}>
        Recent runs{state.total != null ? ` · ${state.total.toLocaleString()}` : ''}
      </summary>
      <div style={{ borderTop: '0.5px solid var(--line)', padding: '6px 10px 9px' }}>
        {state.error ? (
          <p style={{ margin: 4, color: 'var(--ink-4)', fontSize: 11.5 }}>Saved runs are temporarily unavailable.</p>
        ) : state.runs.length === 0 ? (
          <p style={{ margin: 4, color: 'var(--ink-4)', fontSize: 11.5 }}>No saved Batch runs yet.</p>
        ) : (
          <ul style={{ display: 'grid', gap: 5, padding: 0, margin: 0, listStyle: 'none' }}>
            {state.runs.map((run) => (
              <li
                key={run.run_id}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', padding: '7px 8px', borderRadius: 8, background: run.run_id === currentRunId ? 'var(--teal-tint)' : 'var(--bg-soft)' }}
              >
                <span style={{ color: 'var(--ink-3)', fontSize: 11 }}>
                  <strong style={{ color: 'var(--ink-2)' }}>{run.status}</strong>
                  {' · '}{run.done.toLocaleString()} / {run.total.toLocaleString()}
                  {' · '}{new Date(run.updated_at).toLocaleString()}
                </span>
                <span className="flex flex-wrap items-center gap-1.5">
                  <button type="button" onClick={() => onOpen(run.run_id)} style={sourceActionBtn(run.run_id === currentRunId)}>
                    {run.run_id === currentRunId ? 'Open' : 'Resume'}
                  </button>
                  {(run.status === 'queued' || run.status === 'running') && (
                    <button type="button" onClick={() => void onCancel(run.run_id)} style={sourceActionBtn(false)}>Cancel</button>
                  )}
                  {confirmDelete === run.run_id ? (
                    <>
                      <button type="button" onClick={() => setConfirmDelete(null)} style={sourceActionBtn(false)}>Keep</button>
                      <button type="button" onClick={() => { setConfirmDelete(null); void onDelete(run.run_id) }} style={sourceActionBtn(false)}>Confirm delete</button>
                    </>
                  ) : (
                    <button type="button" onClick={() => setConfirmDelete(run.run_id)} style={sourceActionBtn(false)}>Delete</button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  )
}

export function ResumedBatchOutput({
  status,
  progress,
  results,
  resultPage,
  pageIndex,
  onCancel,
  onDelete,
  onExport,
  onPrevious,
  onNext,
  onStartNew,
}: {
  status: RunStatus
  progress: BatchProgress | null
  results: BatchResult[] | null
  resultPage: BatchPage | null
  pageIndex: number
  onCancel: () => void
  onDelete: () => void
  onExport: (format: 'tsv' | 'manifest') => void
  onPrevious: () => void
  onNext: () => void
  onStartNew: () => void
}) {
  const completedEmpty = Array.isArray(results) && results.length === 0 && progress?.stage === 'completed'
  return (
    <section aria-label="Resumed Batch run">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 style={{ margin: 0, color: 'var(--ink)', font: '650 20px var(--display)' }}>Saved Batch run</h1>
          <p style={{ margin: '3px 0 0', color: 'var(--ink-4)', fontSize: 11.5 }}>Owner-scoped server result. Source previews are not restored.</p>
        </div>
        <button type="button" onClick={onStartNew} style={sourceActionBtn(false)}>Start a new cohort</button>
      </div>
      {status === 'idle' || status === 'running' ? (
        <>
          <LoadingCard progress={progress} />
          {progress?.jobId && <div className="mt-3 flex justify-end"><button type="button" onClick={onCancel} style={sourceActionBtn(false)}>Cancel run</button></div>}
        </>
      ) : progress && isBatchIssue(progress.stage) ? (
        <>
          <BatchRunIssue progress={progress} />
          {progress.jobId && <div className="flex justify-end"><DeleteRunButton onDelete={onDelete} /></div>}
        </>
      ) : completedEmpty && progress ? (
        <BatchEmptyRun progress={progress} onClear={onStartNew} />
      ) : results && results.length > 0 ? (
        <>
          <BatchWarnings warnings={progress?.warnings ?? []} />
          <div className="mb-3 flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => onExport('tsv')} style={sourceActionBtn(false)}>Export full TSV</button>
            <button type="button" onClick={() => onExport('manifest')} style={sourceActionBtn(false)}>Export manifest</button>
            <DeleteRunButton onDelete={onDelete} />
          </div>
          <BatchTable rows={results.map(rowFromResult)} annotated activePanels={[]} />
          {resultPage && <BatchPager page={resultPage} pageIndex={pageIndex} onPrevious={onPrevious} onNext={onNext} />}
        </>
      ) : (
        <p role="status" style={{ padding: 14, border: '0.5px solid var(--line)', borderRadius: 10, background: 'var(--bg)', color: 'var(--ink-3)', fontSize: 12.5 }}>
          This saved run has no result page available.
        </p>
      )}
    </section>
  )
}

/** Page context shown in the nav center (breadcrumb + title + cohort size) so
 *  the body leads straight with the output — no tall header band above it. */
export function NavContext({ count, source }: { count: number; source?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0 }}>
      <Link href="/" style={{ fontSize: 12.5, color: 'var(--ink-4)', textDecoration: 'none', whiteSpace: 'nowrap' }}>
        Search
      </Link>
      <span style={{ color: 'var(--ink-5)' }}>/</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', whiteSpace: 'nowrap' }}>Batch</span>
      {count > 0 && (
        <span
          style={{
            fontFamily: 'var(--mono)',
            fontSize: 11.5,
            color: 'var(--ink-4)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          · {count} variant{count === 1 ? '' : 's'}
          {source ? ` · ${source}` : ''}
        </span>
      )}
    </div>
  )
}

export function DeleteRunButton({ onDelete }: { onDelete: () => void }) {
  const [confirming, setConfirming] = useState(false)
  return confirming ? (
    <span className="flex flex-wrap items-center gap-2">
      <button type="button" onClick={() => setConfirming(false)} style={sourceActionBtn(false)}>Keep run</button>
      <button type="button" onClick={onDelete} style={sourceActionBtn(false)}>Confirm delete</button>
    </span>
  ) : (
    <button type="button" onClick={() => setConfirming(true)} style={sourceActionBtn(false)}>Delete run</button>
  )
}

export function Spinner({ light = true }: { light?: boolean }) {
  return (
    <span
      aria-hidden
      style={{
        display: 'inline-block',
        width: 13,
        height: 13,
        marginRight: 7,
        verticalAlign: '-2px',
        borderRadius: '50%',
        border: `2px solid ${light ? 'rgba(255,255,255,0.4)' : 'var(--line-2)'}`,
        borderTopColor: light ? '#fff' : 'var(--teal-deep)',
        animation: 'eamos-spin 0.7s linear infinite',
      }}
    />
  )
}

/** The idle-with-cohort state. Doubles as the "you added something" confirmation:
 *  a cohort is loaded but not yet run, so it names the count + source with a
 *  success accent (the rail un-dimming alone read as too quiet) and points at the
 *  next step — scope, then generate. */
export function GeneratePrompt({
  count,
  source,
  scoped,
  onGenerate,
}: {
  count: number
  source?: string
  scoped: boolean
  onGenerate: () => void
}) {
  return (
    <section
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--teal-bdr)',
        borderTop: '2px solid var(--teal)',
        borderRadius: 14,
        padding: '26px 28px 32px',
        textAlign: 'center',
      }}
    >
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 11px',
          borderRadius: 999,
          background: 'var(--teal-tint)',
          border: '0.5px solid var(--teal-bdr)',
          color: 'var(--teal-deep)',
          fontSize: 11,
          fontWeight: 700,
          fontFamily: 'var(--mono)',
          letterSpacing: '0.03em',
          textTransform: 'uppercase',
        }}
      >
        <IconCheck size={12} /> Cohort loaded
      </span>
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 19, margin: '12px 0 0', color: 'var(--ink)' }}>
        {count} variant{count === 1 ? '' : 's'} ready
        {source ? <span style={{ color: 'var(--ink-3)', fontWeight: 500 }}> · {source}</span> : null}
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--ink-3)', margin: '8px auto 0', maxWidth: 470 }}>
        Scope it with the filters on the left{scoped ? ' (filters applied)' : ''}, then generate to run the
        per-variant lookup. Large VCFs aren’t filtered in real time.
      </p>
      <button type="button" onClick={onGenerate} className="cmp-cta cmp-cta--solid" style={{ marginTop: 18 }}>
        Generate results →
      </button>
    </section>
  )
}

export function LoadingCard({ progress }: { progress: BatchProgress | null }) {
  const done = Math.max(0, progress?.done ?? 0)
  const total = Math.max(0, progress?.total ?? 0)
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0
  const statusLabel =
    progress?.stage === 'uploading'
      ? 'Uploading VCF'
      : progress?.status === 'queued' || progress?.stage === 'queued'
        ? 'Queued'
        : progress?.status === 'running' || progress?.stage === 'running'
          ? 'Running lookup'
          : progress?.status === 'completed' || progress?.stage === 'completed'
            ? 'Completed'
            : 'Preparing job'

  return (
    <section
      aria-live="polite"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '24px 26px',
        color: 'var(--ink-2)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
          <Spinner light={false} />
          <span style={{ fontSize: 14, fontWeight: 650, color: 'var(--ink)' }}>{statusLabel}</span>
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
          {total > 0 ? `${done} / ${total}` : 'waiting'}
          {progress?.usedUpload ? ' · server parsed' : ''}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label="Batch lookup progress"
        aria-valuemin={0}
        aria-valuemax={total || 100}
        aria-valuenow={total > 0 ? done : undefined}
        style={{
          position: 'relative',
          height: 9,
          borderRadius: 999,
          background: 'var(--bg-soft2)',
          border: '0.5px solid var(--line)',
          overflow: 'hidden',
          marginTop: 15,
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            width: `${pct}%`,
            background: 'var(--teal-deep)',
            borderRadius: 999,
            transition: 'width var(--dur-2) var(--ease-standard)',
          }}
        />
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 11, fontSize: 11.5, color: 'var(--ink-4)' }}>
        {progress?.nInput != null && <span>Input {progress.nInput.toLocaleString()}</span>}
        {progress?.nToLookup != null && <span>Lookup {progress.nToLookup.toLocaleString()}</span>}
        {progress?.estSeconds != null && progress.estSeconds > 0 && <span>Est. {Math.ceil(progress.estSeconds)}s</span>}
        {progress?.jobId && <span style={{ fontFamily: 'var(--mono)' }}>{progress.jobId}</span>}
      </div>
    </section>
  )
}

export function BatchPager({
  page,
  pageIndex,
  onPrevious,
  onNext,
}: {
  page: BatchPage
  pageIndex: number
  onPrevious: () => void
  onNext: () => void
}) {
  const start = pageIndex * page.limit + 1
  const end = Math.min(page.total, start + page.limit - 1)
  return (
    <nav
      className="mt-3 flex flex-wrap items-center justify-between gap-3"
      aria-label="Batch result pages"
      style={{
        border: '0.5px solid var(--line)',
        borderRadius: 10,
        background: 'var(--bg)',
        padding: '9px 11px',
      }}
    >
      <span style={{ fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--ink-4)' }}>
        {page.total === 0 ? 'No rows' : `${start.toLocaleString()}–${end.toLocaleString()} of ${page.total.toLocaleString()}`}
        {' · '}at most {page.limit} rows mounted
      </span>
      <span className="flex items-center gap-2">
        <button type="button" onClick={onPrevious} disabled={pageIndex === 0} style={sourceActionBtn(false)}>
          Previous
        </button>
        <button type="button" onClick={onNext} disabled={!page.next_cursor} style={sourceActionBtn(false)}>
          Next
        </button>
      </span>
    </nav>
  )
}

export function BatchRunIssue({ progress }: { progress: BatchProgress }) {
  const copy = issueCopy(progress)
  return (
    <section
      role="alert"
      style={{
        background: copy.tone === 'error' ? 'var(--err-tint)' : 'var(--warn-tint)',
        border: `0.5px solid ${copy.tone === 'error' ? 'var(--err-bdr, var(--err))' : 'var(--warn-bdr)'}`,
        borderRadius: 14,
        padding: '20px 22px',
        color: copy.tone === 'error' ? 'var(--err)' : 'var(--warn-text)',
        marginBottom: 14,
      }}
    >
      <h2 style={{ fontSize: 14, fontWeight: 650, color: 'inherit', margin: 0 }}>{copy.title}</h2>
      <p style={{ fontSize: 12.5, lineHeight: 1.6, margin: '7px 0 0' }}>
        {copy.body}
      </p>
      {progress.stage === 'auth' && (
        <button type="button" onClick={openAuthMenu} style={{ ...sourceActionBtn(false), marginTop: 10 }}>
          Sign in
        </button>
      )}
      {progress.done > 0 || progress.total > 0 ? (
        <p style={{ fontFamily: 'var(--mono)', fontSize: 11.5, margin: '9px 0 0' }}>
          {progress.done} / {progress.total} variants completed
        </p>
      ) : null}
      <BatchWarnings warnings={progress.warnings ?? []} compact />
    </section>
  )
}

export function BatchEmptyRun({ progress, onClear }: { progress: BatchProgress; onClear: () => void }) {
  const nInput = progress.nInput ?? 0
  const nAfterFilters = progress.nAfterFilters ?? progress.nToLookup ?? 0
  return (
    <section
      aria-live="polite"
      style={{
        background: 'var(--bg)',
        border: '0.5px solid var(--line)',
        borderRadius: 14,
        padding: '22px 24px',
        color: 'var(--ink-2)',
      }}
    >
      <h2 style={{ fontFamily: 'var(--display)', fontWeight: 600, fontSize: 15, margin: 0, color: 'var(--ink)' }}>
        No variants to annotate after filters
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.6, margin: '8px 0 0', color: 'var(--ink-3)' }}>
        The Batch run completed, but the active scope removed every input variant. Widen the scope or clear the filters, then regenerate.
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 11, fontSize: 11.5, color: 'var(--ink-4)' }}>
        {nInput > 0 && <span>Input {nInput.toLocaleString()}</span>}
        <span>After filters {nAfterFilters.toLocaleString()}</span>
        {progress.jobId && <span style={{ fontFamily: 'var(--mono)' }}>{progress.jobId}</span>}
      </div>
      <button
        type="button"
        onClick={onClear}
        style={{
          marginTop: 14,
          padding: '7px 14px',
          borderRadius: 10,
          border: '0.5px solid var(--line-2)',
          background: 'var(--bg)',
          color: 'var(--ink-2)',
          fontSize: 12.5,
          fontWeight: 600,
          cursor: 'pointer',
        }}
      >
        Clear all filters
      </button>
      <BatchWarnings warnings={progress.warnings ?? []} compact />
    </section>
  )
}

export function StaleRunNotice() {
  return (
    <section
      aria-live="polite"
      style={{
        background: 'var(--warn-tint)',
        border: '0.5px solid var(--warn-bdr)',
        borderRadius: 12,
        padding: '10px 13px',
        marginBottom: 12,
        color: 'var(--warn-text)',
        fontSize: 12.5,
        lineHeight: 1.45,
      }}
    >
      Showing the previous Batch run. Regenerate to apply the current scope.
    </section>
  )
}

export function PreviewLimitNotice({ total }: { total: number }) {
  return (
    <p
      role="status"
      style={{
        margin: '0 0 10px',
        padding: '9px 11px',
        borderRadius: 9,
        border: '0.5px solid var(--line)',
        background: 'var(--bg-soft)',
        color: 'var(--ink-3)',
        fontSize: 12,
      }}
    >
      Showing the first 500 of {total.toLocaleString()} preview rows. Generate the run for server-paged results.
    </p>
  )
}

export function BatchWarnings({ warnings, compact = false }: { warnings: string[]; compact?: boolean }) {
  const unique = Array.from(new Set(warnings.filter(Boolean)))
  if (unique.length === 0) return null
  const shown = unique.slice(0, compact ? 3 : 5)
  const remaining = unique.length - shown.length
  return (
    <section
      aria-label="Batch warnings"
      style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 8,
        flexWrap: 'wrap',
        margin: compact ? '12px 0 0' : '0 0 12px',
        padding: compact ? 0 : '9px 11px',
        borderRadius: compact ? undefined : 12,
        border: compact ? undefined : '0.5px solid var(--line)',
        background: compact ? undefined : 'var(--bg-soft)',
      }}
    >
      <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--ink-4)' }}>
        Warnings
      </span>
      {shown.map((warning) => (
        <span
          key={warning}
          title={warning}
          style={{
            maxWidth: 260,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontFamily: 'var(--mono)',
            fontSize: 10.5,
            color: 'var(--ink-3)',
            padding: '2px 6px',
            borderRadius: 6,
            border: '0.5px solid var(--line-2)',
            background: 'var(--bg)',
          }}
        >
          {warning}
        </span>
      ))}
      {remaining > 0 && (
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-4)' }}>+{remaining} more</span>
      )}
    </section>
  )
}

export function sourceActionBtn(active: boolean): CSSProperties {
  return {
    minHeight: 44,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
    padding: '5px 10px',
    borderRadius: 9,
    border: `0.5px solid ${active ? 'var(--teal-bdr)' : 'var(--line-2)'}`,
    background: active ? 'var(--teal-tint)' : 'var(--bg)',
    color: active ? 'var(--teal-deep)' : 'var(--ink-2)',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
  }
}
