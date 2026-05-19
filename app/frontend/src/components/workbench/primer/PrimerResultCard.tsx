import { useId, useRef, useState } from 'react'
import type { PrimerPair } from '@/lib/backend'
import { classifyPair, parseNotes } from '@/lib/workbench/primer-metrics'

/* ───────────────────────────────────────────────────────────────────────
   PrimerResultCard — the canonical reference implementation of the
   DESIGN.md "Dashboard Interaction Language" 3-layer progressive-disclosure
   pattern (plans/primer-integration.md §5). Later CRISPR/Align/Compare/Report
   modules migrate to this shape as their own gated passes.

   Layer 1  decision surface  (always visible): badge + identity + Copy.
   Layer 2  primary detail    (always visible): sequences, Tm/GC, product.
   Layer 3  deep dive         (hidden): thermo profile + specificity prose.

   Disclosure: the plan asks for <details>/summary *semantics* with an
   animated height+opacity reveal. Native <details> cannot animate height
   reliably cross-browser, and DESIGN.md mandates the grid-rows technique for
   the one sanctioned size transition — so this uses the equivalent ARIA
   disclosure pattern (button[aria-expanded] + aria-controls) over a
   grid-template-rows 0fr→1fr wrap. Same semantics, animatable, a11y-clean.
─────────────────────────────────────────────────────────────────────── */

/** Select the chip's text on click — order-ready copy without a textarea. */
function selectText(el: HTMLElement) {
  const sel = window.getSelection()
  if (!sel) return
  const range = document.createRange()
  range.selectNodeContents(el)
  sel.removeAllRanges()
  sel.addRange(range)
}

function PrimerTip({ label, tip }: { label: string; tip: string }) {
  // Focusable trigger; the explanation is on aria-label (screen readers get
  // it directly) and shown visually on hover/focus-within via CSS.
  return (
    <span className="primer-tip">
      {label}
      <button
        type="button"
        className="primer-tip-q"
        aria-label={`${label}: ${tip}`}
      >
        ?
      </button>
      <span className="primer-tip-pop" role="tooltip">
        {tip}
      </span>
    </span>
  )
}

interface PrimerResultCardProps {
  pair: PrimerPair
}

export function PrimerResultCard({ pair }: PrimerResultCardProps) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState<'idle' | 'ok' | 'fail'>('idle')
  const fwdRef = useRef<HTMLSpanElement>(null)
  const revRef = useRef<HTMLSpanElement>(null)
  const drawerId = useId()

  const { badge, deltaTm, deltaTmWarn } = classifyPair(pair)
  const notes = parseNotes(pair.notes)

  const copyPair = async () => {
    const text = `F: ${pair.forward}\nR: ${pair.reverse}`
    try {
      await navigator.clipboard.writeText(text)
      setCopied('ok')
    } catch {
      setCopied('fail')
    }
    window.setTimeout(() => setCopied('idle'), 1600)
  }

  return (
    <article
      className={`primer-card card--interactive${pair.recommended ? ' rec' : ''}`}
    >
      {/* ── Layer 1 — decision surface ─────────────────────────────── */}
      <header className="primer-l1">
        <span className={`primer-badge tone-${badge.tone}`}>
          <i className="primer-badge-dot" />
          {badge.label}
        </span>
        <span className="primer-l1-id">
          {pair.recommended && <span className="primer-star" aria-hidden>★</span>}
          Primer pair #{pair.index}
          {pair.recommended && <span className="sr-only"> (recommended)</span>}
        </span>
        <button
          type="button"
          className="primer-copy"
          onClick={copyPair}
          aria-live="polite"
        >
          {copied === 'ok'
            ? 'Copied'
            : copied === 'fail'
              ? 'Copy failed'
              : 'Copy pair'}
        </button>
      </header>

      {/* ── Layer 2 — primary detail ───────────────────────────────── */}
      <div className="primer-l2">
        <div className="primer-strand">
          <span className="primer-strand-tag">F</span>
          <span
            ref={fwdRef}
            className="primer-seq"
            title="Click to select"
            onClick={() => fwdRef.current && selectText(fwdRef.current)}
          >
            {pair.forward}
          </span>
          <span className="primer-strand-m">
            Tm <b>{pair.tm_forward.toFixed(1)}</b> · GC <b>{pair.gc_forward}%</b>
          </span>
        </div>
        <div className="primer-strand">
          <span className="primer-strand-tag">R</span>
          <span
            ref={revRef}
            className="primer-seq"
            title="Click to select"
            onClick={() => revRef.current && selectText(revRef.current)}
          >
            {pair.reverse}
          </span>
          <span className="primer-strand-m">
            Tm <b>{pair.tm_reverse.toFixed(1)}</b> · GC <b>{pair.gc_reverse}%</b>
          </span>
        </div>
        <div className="primer-l2-foot">
          <span className="primer-product">
            Product <b>{pair.product_size} bp</b>
          </span>
          <span
            className={`primer-dtm${deltaTmWarn ? ' warn' : ''}`}
            title={
              deltaTmWarn
                ? 'ΔTm > 2 °C — primers may anneal at different temperatures'
                : 'Forward / reverse Tm are well matched'
            }
          >
            ΔTm {deltaTm.toFixed(1)} °C
          </span>
        </div>
      </div>

      {/* ── Layer 3 — deep dive (hidden by default) ────────────────── */}
      <button
        type="button"
        className="primer-l3-summary"
        aria-expanded={open}
        aria-controls={drawerId}
        onClick={() => setOpen((o) => !o)}
      >
        <svg
          className={`primer-chev${open ? ' open' : ''}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span>Audit detail</span>
        <span className="primer-l3-hint">thermodynamics · specificity</span>
      </button>
      <div className={`primer-l3-wrap${open ? ' open' : ''}`}>
        <div className="primer-l3-inner" id={drawerId} hidden={!open}>
          <div className="primer-l3-grid">
            <section>
              <h4 className="primer-l3-h">
                <PrimerTip
                  label="Thermodynamics"
                  tip="Melting temperature (Tm) and GC content per primer, plus the pair ΔTm. Balanced Tm (ΔTm ≤ 2 °C) and 35–70% GC give clean, specific amplification."
                />
              </h4>
              <dl className="primer-kv">
                <div>
                  <dt>Tm pair</dt>
                  <dd>
                    {pair.tm_forward.toFixed(1)} / {pair.tm_reverse.toFixed(1)} °C
                  </dd>
                </div>
                <div>
                  <dt>GC pair</dt>
                  <dd>
                    {pair.gc_forward}% / {pair.gc_reverse}%
                  </dd>
                </div>
                <div>
                  <dt>ΔTm</dt>
                  <dd className={deltaTmWarn ? 'warn' : undefined}>
                    {deltaTm.toFixed(1)} °C
                  </dd>
                </div>
                <div>
                  <dt>Product size</dt>
                  <dd>{pair.product_size} bp</dd>
                </div>
              </dl>
            </section>
            <section>
              <h4 className="primer-l3-h">
                <PrimerTip
                  label="Specificity"
                  tip="How many products the specificity screen found and what the design engine reported. Whole-genome specificity needs the UCSC isPcr provider; the default template provider screens the resolved window only — this is not an NCBI Primer-BLAST validation."
                />
              </h4>
              <dl className="primer-kv">
                <div>
                  <dt>Hits</dt>
                  <dd className={pair.specificity_hits === 1 ? undefined : 'warn'}>
                    {pair.specificity_hits}
                  </dd>
                </div>
                {notes.provider && (
                  <div>
                    <dt>Provider</dt>
                    <dd>{notes.provider}</dd>
                  </div>
                )}
                {notes.productSizes && (
                  <div>
                    <dt>Products</dt>
                    <dd>{notes.productSizes}</dd>
                  </div>
                )}
                {notes.spansTarget !== undefined && (
                  <div>
                    <dt>Spans target</dt>
                    <dd className={notes.spansTarget ? undefined : 'warn'}>
                      {notes.spansTarget ? 'yes' : 'no'}
                    </dd>
                  </div>
                )}
              </dl>
              <p className="primer-notes-raw">{notes.raw || '—'}</p>
              {notes.primerBlastCaveat && (
                <p className="primer-caveat">{notes.primerBlastCaveat}</p>
              )}
            </section>
          </div>
        </div>
      </div>
    </article>
  )
}
