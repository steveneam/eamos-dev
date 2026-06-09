/**
 * Feedback-intake mailto for the account menu. Lifted from the retired
 * bottom-left CiteChip dock (docs/workbench-task-a Part A). Hook-free so the
 * globally-mounted AuthMenu never pulls useSearchParams (which would force a
 * Suspense boundary around the rail foot on every surface) — it reads
 * window.location at click-time instead.
 *
 * NOTE: the Cite citation modal was removed product-wide on 2026-06-10 (Steven).
 * Its plumbing (useCiteModal hook + CiteModal.tsx) is recoverable from git if
 * Cite returns.
 */

const FEEDBACK_TO = 'sales@eamos.com.au'
const REPORT_VERSION = '2026.05'

/** {variant_display} from /report URL params; null off /report. */
function resolveVariantDisplay(pathname: string, search: string): string | null {
  if (pathname !== '/report') return null
  const p = new URLSearchParams(search)
  const gene = p.get('gene')?.trim()
  const cdna = p.get('cdna')?.trim()
  const protein = p.get('protein_change')?.trim()
  const q = p.get('q')?.trim()
  const fixture = p.get('fixture')?.trim()
  if (gene && cdna) return [gene, cdna, protein ? `(${protein})` : ''].filter(Boolean).join(' ').trim()
  if (q) return q
  if (fixture === 'rpe65-negative') return 'RPE65 c.260A>G'
  return 'USH2A c.2276G>T'
}

/** Feedback mailto — current page URL + (on /report) variant prefilled, built at
 *  call-time from window.location (no hooks). */
export function buildFeedbackMailto(): string {
  if (typeof window === 'undefined') return `mailto:${FEEDBACK_TO}`
  const { pathname, search, href } = window.location
  const variant = resolveVariantDisplay(pathname, search)
  const subject = `Eamos feedback${variant ? ` — ${variant}` : ''}`
  const body = `\n\n--\nPage: ${href}${variant ? `\nVariant: ${variant}` : ''}\nReport version: ${REPORT_VERSION}`
  return `mailto:${FEEDBACK_TO}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}
