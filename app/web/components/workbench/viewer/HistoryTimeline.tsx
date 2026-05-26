'use client'
import type { HistoryStep } from '@/lib/workbench/edit-state'

interface HistoryTimelineProps {
  history: HistoryStep[]
  cursor: number
  onJump: (to: number) => void
}

const fmt = (t: number) =>
  new Date(t).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

/** Edit-history drawer (toggle; hidden by default). Port of
 *  `renderHistoryTimeline()`. */
export function HistoryTimeline({ history, cursor, onJump }: HistoryTimelineProps) {
  return (
    <div className="sv-history">
      <div className="sv-history-head">
        <span className="lbl">Edit history</span>
        <span className="meta">
          {history.length} step{history.length === 1 ? '' : 's'} · cursor {cursor}/
          {history.length}
        </span>
      </div>
      <div className="sv-history-list">
        {history.map((h, i) => (
          <button
            key={i}
            type="button"
            className={`sv-history-row ${i < cursor ? 'applied' : 'undone'}${
              i === cursor - 1 ? ' current' : ''
            }`}
            onClick={() => onJump(i + 1)}
          >
            <span className="dot" />
            <span className="num">{i + 1}</span>
            <span className="lbl">{h.label}</span>
            <span className="t">{fmt(h.time)}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
