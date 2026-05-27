/* ───────────────────────────────────────────────────────────────────────
   CRISPR guide → design-template mapping (pure, testable).

   The Blueprint-1 reference dashboard's signature interaction is a
   row-hover ribbon that paints the spacer + PAM (and the predicted blunt
   cut) onto the sequence the guides were designed against. Eamos rebuilds
   that as `GuideTrack`; this module owns the deterministic placement math
   so it can be unit-tested without a DOM.

   Coordinate note: the existing `/api/v1/crispr` fixture reports
   `cut_position` as a *design-template-local* offset (24–31), NOT an RPE65
   CDS coordinate (the viewer window is c.217–339). Mapping the spacer onto
   the gene-window via `cut_position` would therefore place guides in the
   wrong place. We instead locate the spacer inside the design template the
   guides were actually scored against — the ssODN reference arm — exactly
   as the blueprint dashboard works off its submitted sequence. The §6
   Codex backend brief tracks reconciling `cut_position` semantics.
─────────────────────────────────────────────────────────────────────── */

import type { CrisprGuide } from '@/lib/backend'

const COMPLEMENT: Record<string, string> = { A: 'T', T: 'A', C: 'G', G: 'C' }

/** Reverse complement of an A/T/C/G string (unknown chars pass through). */
export function revComp(seq: string): string {
  return seq
    .toUpperCase()
    .split('')
    .reverse()
    .map((c) => COMPLEMENT[c] ?? c)
    .join('')
}

export interface GuideMap {
  /** Did we locate the spacer (or its reverse complement) in the template? */
  located: boolean
  /** Spacer span on the template's + strand, [start, end) (end exclusive). */
  spacerStart: number
  spacerEnd: number
  /** Spacer as it sits on the + strand (== guide for '+', revComp for '-'). */
  spacerOnPlus: string
  /** PAM span on the + strand, or null when it runs off the template edge. */
  pamStart: number | null
  pamEnd: number | null
  /** Predicted blunt-cut boundary index on the + strand (Cas9: 3 bp from
   *  the PAM-proximal end of the spacer), or null when unknown. */
  cutIndex: number | null
}

const NOT_LOCATED: GuideMap = {
  located: false,
  spacerStart: -1,
  spacerEnd: -1,
  spacerOnPlus: '',
  pamStart: null,
  pamEnd: null,
  cutIndex: null,
}

/**
 * Locate `guide` within `template` and resolve its PAM + predicted cut.
 *
 * Cas9 geometry: the PAM (e.g. NGG) sits immediately 3′ of the spacer and
 * the blunt cut falls 3 bp 5′ of the PAM. For a '+' guide the spacer is
 * matched directly; for a '-' guide its reverse complement is matched onto
 * the + strand, so the PAM lies immediately 5′ of the matched region and
 * the cut sits 3 bp into the matched region from that 5′ edge.
 */
export function mapGuide(guide: CrisprGuide, template: string): GuideMap {
  const tpl = template.toUpperCase()
  const onPlus =
    guide.strand === '-' ? revComp(guide.guide) : guide.guide.toUpperCase()
  const start = tpl.indexOf(onPlus)
  if (start < 0) return { ...NOT_LOCATED, spacerOnPlus: onPlus }

  const end = start + onPlus.length
  const pamLen = guide.pam.length

  if (guide.strand === '-') {
    // PAM is 5′ of the matched spacer on the + strand; cut 3 bp inward.
    const pStart = start - pamLen
    return {
      located: true,
      spacerStart: start,
      spacerEnd: end,
      spacerOnPlus: onPlus,
      pamStart: pStart >= 0 ? pStart : null,
      pamEnd: pStart >= 0 ? start : null,
      cutIndex: start + 3,
    }
  }

  // '+' (and unknown): PAM is 3′ of the spacer; cut 3 bp from the 3′ end.
  const pEnd = end + pamLen
  return {
    located: true,
    spacerStart: start,
    spacerEnd: end,
    spacerOnPlus: onPlus,
    pamStart: pEnd <= tpl.length ? end : null,
    pamEnd: pEnd <= tpl.length ? pEnd : null,
    cutIndex: end - 3,
  }
}
