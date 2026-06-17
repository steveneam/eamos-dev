'use client'
// Root error boundary (App Router). Renders only when the root layout itself
// throws — a rare, catastrophic case where NONE of the app's CSS, fonts, or
// providers are guaranteed to have loaded. So this page is fully self-contained:
// its own <html>/<body>, every style in one injected <style> block (pseudo-
// classes, reduced-motion, keyframes — things inline styles can't express), and
// font stacks that degrade to a warm system serif/sans if Spectral/Inter aren't
// cached. Reports to Sentry and offers two real recovery paths.
import * as Sentry from '@sentry/nextjs'
import { useEffect } from 'react'

const STYLES = `
.eamos-err *, .eamos-err *::before, .eamos-err *::after { box-sizing: border-box; }
.eamos-err {
  margin: 0; min-height: 100vh; min-height: 100dvh;
  display: flex; align-items: center; justify-content: center; padding: 24px;
  background: radial-gradient(125% 85% at 50% -12%, oklch(98.2% 0.014 80) 0%, oklch(99.3% 0.004 75) 54%);
  color: oklch(24% 0.018 48);
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
}
.eamos-err__wrap { width: 100%; max-width: 30rem; text-align: center; }
.eamos-err__brand { display: inline-flex; align-items: center; gap: 7px; margin-bottom: 38px; }
.eamos-err__brand-name {
  font-family: 'Spectral', 'Newsreader', Georgia, 'Times New Roman', serif;
  font-size: 18px; font-weight: 600; letter-spacing: 0.01em; color: oklch(31% 0.02 47);
}
.eamos-err__medallion {
  width: 60px; height: 60px; margin: 0 auto 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: oklch(97.4% 0.012 72); border: 1px solid oklch(89% 0.01 60);
  box-shadow: 0 1px 0 oklch(100% 0 0 / 0.6) inset, 0 8px 22px -16px oklch(40% 0.04 50 / 0.5);
}
.eamos-err__title {
  font-family: 'Spectral', 'Newsreader', Georgia, 'Times New Roman', serif;
  font-weight: 500; font-size: clamp(25px, 5.2vw, 31px); line-height: 1.18;
  letter-spacing: -0.005em; margin: 0 0 12px; color: oklch(23% 0.02 46);
}
.eamos-err__body { font-size: 14.5px; line-height: 1.62; color: oklch(46% 0.028 47); margin: 0 auto; max-width: 34ch; }
.eamos-err__actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 10px 18px; margin-top: 28px; }
.eamos-err__btn {
  appearance: none; border: 1px solid #156b50; background: #156b50; color: oklch(99% 0.004 75);
  font: inherit; font-size: 14px; font-weight: 600; min-height: 44px; padding: 0 22px; border-radius: 11px;
  cursor: pointer; display: inline-flex; align-items: center; gap: 8px;
  box-shadow: 0 8px 20px -12px oklch(48% 0.09 165 / 0.7);
  transition: background .18s cubic-bezier(.2,.8,.2,1), transform .18s cubic-bezier(.2,.8,.2,1), box-shadow .18s;
}
.eamos-err__btn:hover { background: #125e46; transform: translateY(-1px); box-shadow: 0 12px 26px -12px oklch(48% 0.09 165 / 0.78); }
.eamos-err__btn:active { transform: translateY(0); }
.eamos-err__link {
  font: inherit; font-size: 14px; font-weight: 500; color: oklch(33% 0.035 45);
  text-decoration: none; background: none; border: 0; cursor: pointer; min-height: 44px;
  display: inline-flex; align-items: center; padding: 0 4px;
  border-bottom: 1px solid transparent; transition: color .18s, border-color .18s;
}
.eamos-err__link:hover { color: oklch(23% 0.02 46); border-bottom-color: oklch(70% 0.02 55); }
.eamos-err__ref {
  margin: 30px 0 0; font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11.5px; letter-spacing: 0.02em; color: oklch(45% 0.02 58);
}
.eamos-err__ref b { font-weight: 500; color: oklch(37% 0.025 52); }
.eamos-err :focus-visible { outline: 2px solid #156b50; outline-offset: 3px; border-radius: 7px; }
@media (prefers-reduced-motion: no-preference) {
  .eamos-err__brand, .eamos-err__medallion, .eamos-err__title, .eamos-err__body, .eamos-err__actions, .eamos-err__ref {
    opacity: 0; transform: translateY(9px); animation: eamosErrIn .6s cubic-bezier(.2,.8,.2,1) forwards;
  }
  .eamos-err__medallion { animation-delay: .05s; }
  .eamos-err__title { animation-delay: .1s; }
  .eamos-err__body { animation-delay: .16s; }
  .eamos-err__actions { animation-delay: .22s; }
  .eamos-err__ref { animation-delay: .3s; }
}
@keyframes eamosErrIn { to { opacity: 1; transform: none; } }
`

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    Sentry.captureException(error)
  }, [error])

  return (
    <html lang="en">
      <body>
        <style dangerouslySetInnerHTML={{ __html: STYLES }} />
        <main className="eamos-err">
          <div className="eamos-err__wrap">
            <span className="eamos-err__brand">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="#156b50" aria-hidden="true">
                <path d="M12 1.6l1.85 6.6a3.4 3.4 0 0 0 1.94 1.95L22.4 12l-6.61 1.85a3.4 3.4 0 0 0-1.94 1.95L12 22.4l-1.85-6.6a3.4 3.4 0 0 0-1.94-1.95L1.6 12l6.61-1.85a3.4 3.4 0 0 0 1.94-1.95z" />
              </svg>
              <span className="eamos-err__brand-name">Eamos</span>
            </span>

            <div className="eamos-err__medallion" aria-hidden="true">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#BA7517" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7.6v5" />
                <path d="M12 16.2h.01" />
              </svg>
            </div>

            <h1 className="eamos-err__title">Something interrupted this page</h1>
            <p className="eamos-err__body">
              An unexpected error stopped it from loading. The issue has been logged, so the team can
              look into it. Try again, or return to the start.
            </p>

            <div className="eamos-err__actions">
              <button type="button" className="eamos-err__btn" onClick={() => reset()}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M19 12a7 7 0 1 1-2.05-4.95" />
                  <path d="M19 4v4h-4" />
                </svg>
                Try again
              </button>
              {/* Intentional hard navigation, not <Link>: the root layout has crashed,
                  so a full document reload is the reliable recovery (client-side routing
                  may be broken too). */}
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
              <a className="eamos-err__link" href="/">
                Return to homepage
              </a>
            </div>

            {error.digest ? (
              <p className="eamos-err__ref">
                Reference <b>{error.digest}</b>
              </p>
            ) : null}
          </div>
        </main>
      </body>
    </html>
  )
}
