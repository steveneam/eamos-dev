type SurfaceLoadingShellProps = {
  surface: 'report' | 'paper' | 'compare'
}

const LABELS = {
  report: { title: 'Variant report', detail: 'Preparing evidence sections' },
  paper: { title: 'Paper → Variants', detail: 'Preparing publication intake' },
  compare: { title: 'Batch', detail: 'Preparing cohort workspace' },
} as const

export function SurfaceLoadingShell({ surface }: SurfaceLoadingShellProps) {
  const label = LABELS[surface]
  return (
    <div className="surface-shell" data-surface={surface} role="status" aria-label={`Loading ${label.title}`}>
      <header className="surface-shell-nav">
        <span className="surface-shell-logo">Eamos</span>
        <span className="surface-shell-search" />
        <span className="surface-shell-mode">{label.title}</span>
      </header>
      <div className="surface-shell-frame">
        <aside className="surface-shell-rail" aria-hidden>
          <span className="surface-shell-line short" />
          <span className="surface-shell-block" />
          <span className="surface-shell-block small" />
        </aside>
        <main className="surface-shell-main">
          <p className="surface-shell-kicker">{label.detail}</p>
          <span className="surface-shell-heading" aria-hidden />
          {surface === 'report' && (
            <>
              <span className="surface-shell-card hero" aria-hidden />
              <div className="surface-shell-grid" aria-hidden>
                <span className="surface-shell-card" />
                <span className="surface-shell-card" />
                <span className="surface-shell-card" />
              </div>
              <span className="surface-shell-card report-section" aria-hidden />
            </>
          )}
          {surface === 'paper' && (
            <>
              <span className="surface-shell-copy" aria-hidden />
              <span className="surface-shell-card paper-drop" aria-hidden />
              <span className="surface-shell-card paper-text" aria-hidden />
            </>
          )}
          {surface === 'compare' && (
            <>
              <span className="surface-shell-card compare-intake" aria-hidden />
              <div className="surface-shell-table" aria-hidden>
                {Array.from({ length: 6 }, (_, index) => <span key={index} />)}
              </div>
            </>
          )}
        </main>
      </div>
      <style>{`
        .surface-shell { min-height: 100vh; background: var(--bg-soft); color: var(--ink); }
        .surface-shell-nav { height: 58px; display: grid; grid-template-columns: auto minmax(120px, 640px) auto; align-items: center; justify-content: space-between; gap: 24px; padding: 0 24px; border-bottom: 0.5px solid var(--line); background: var(--bg); }
        .surface-shell-logo { font: 650 18px var(--display); }
        .surface-shell-search { width: 100%; height: 34px; border-radius: 999px; background: var(--bg-soft2); }
        .surface-shell-mode { font: 600 11px var(--body); color: var(--ink-4); }
        .surface-shell-frame { min-height: calc(100vh - 58px); display: grid; grid-template-columns: 276px minmax(0, 1fr); }
        .surface-shell-rail { display: grid; align-content: start; gap: 12px; padding: 22px 18px; border-right: 0.5px solid var(--line); background: var(--bg); }
        .surface-shell-line, .surface-shell-block, .surface-shell-heading, .surface-shell-copy, .surface-shell-card, .surface-shell-table span { display: block; background: linear-gradient(90deg, var(--bg-soft2), var(--bg), var(--bg-soft2)); background-size: 220% 100%; animation: surface-shell-shimmer 1.8s ease-in-out infinite; }
        .surface-shell-line { height: 12px; border-radius: 5px; }
        .surface-shell-line.short { width: 44%; }
        .surface-shell-block { height: 112px; border-radius: 10px; }
        .surface-shell-block.small { height: 72px; }
        .surface-shell-main { width: min(100%, 1160px); margin: 0 auto; padding: 28px 32px 72px; }
        .surface-shell-kicker { margin: 0 0 10px; color: var(--ink-4); font: 600 11px var(--body); letter-spacing: 0.04em; text-transform: uppercase; }
        .surface-shell-heading { width: min(340px, 70%); height: 30px; border-radius: 7px; margin-bottom: 18px; }
        .surface-shell-copy { width: min(680px, 90%); height: 13px; border-radius: 5px; margin: -8px 0 20px; }
        .surface-shell-card { height: 128px; border: 0.5px solid var(--line); border-radius: 13px; }
        .surface-shell-card.hero { height: 154px; }
        .surface-shell-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
        .surface-shell-grid .surface-shell-card { height: 96px; }
        .surface-shell-card.report-section { height: 260px; margin-top: 12px; }
        .surface-shell-card.paper-drop { height: 156px; }
        .surface-shell-card.paper-text { height: 132px; margin-top: 12px; }
        .surface-shell-card.compare-intake { height: 116px; margin-bottom: 16px; }
        .surface-shell-table { display: grid; gap: 1px; overflow: hidden; border: 0.5px solid var(--line); border-radius: 12px; background: var(--line); }
        .surface-shell-table span { height: 52px; }
        @keyframes surface-shell-shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
        @media (prefers-reduced-motion: reduce) { .surface-shell-line, .surface-shell-block, .surface-shell-heading, .surface-shell-copy, .surface-shell-card, .surface-shell-table span { animation: none; } }
        @media (max-width: 760px) {
          .surface-shell-nav { grid-template-columns: auto minmax(80px, 1fr); padding: 0 14px; gap: 12px; }
          .surface-shell-mode { display: none; }
          .surface-shell-frame { display: block; }
          .surface-shell-rail { display: none; }
          .surface-shell-main { padding: 22px 16px 56px; }
        }
        @media (max-width: 420px) { .surface-shell-grid { grid-template-columns: 1fr; } .surface-shell-grid .surface-shell-card:nth-child(n+2) { display: none; } }
      `}</style>
    </div>
  )
}
