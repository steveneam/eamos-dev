/* ───────────────────────────────────────────────────────────────────────
   Primer panel — pure, testable core (no React, no DOM).

   `classifyPair`  — the badge taxonomy from plans/primer-integration.md §5.1,
                      mapped onto the frozen `PrimerPair` contract (no recompute
                      of `recommended`; the backend already picks it).
   `parseNotes`    — defensive extraction of the soft-contract `notes` prose.
                      `notes` is prose, not schema: the parser must NEVER throw
                      and must degrade to the raw string when patterns miss.
                      The §6 additive `specificity_detail` field is the durable
                      fix; until then this is the honest best-effort.
─────────────────────────────────────────────────────────────────────── */

import type { PrimerPair } from '@/lib/backend'

export type BadgeTone = 'teal' | 'warn' | 'err'

export interface PrimerBadge {
  key: 'specific' | 'thermo' | 'offtarget' | 'orientation'
  label: string
  tone: BadgeTone
}

export interface ParsedNotes {
  provider?: string
  productSizes?: string
  /** true / false only when notes is explicit; undefined = unknown. */
  spansTarget?: boolean
  primerBlastCaveat?: string
  raw: string
}

/** GC outside this band is a thermodynamic flag (plans §5.1 / §5.2). */
const GC_MIN = 35
const GC_MAX = 70
/** ΔTm above this (°C) is a thermodynamic flag (plans §5.2). */
const DELTA_TM_LIMIT = 2

export interface PairClassification {
  badge: PrimerBadge
  deltaTm: number
  deltaTmWarn: boolean
  gcOutOfBand: boolean
  thermoFlag: boolean
  spansTarget?: boolean
}

export function classifyPair(pair: PrimerPair): PairClassification {
  const deltaTm = Math.abs(pair.tm_forward - pair.tm_reverse)
  const deltaTmWarn = deltaTm > DELTA_TM_LIMIT
  const gcOutOfBand =
    pair.gc_forward < GC_MIN ||
    pair.gc_forward > GC_MAX ||
    pair.gc_reverse < GC_MIN ||
    pair.gc_reverse > GC_MAX
  const thermoFlag = deltaTmWarn || gcOutOfBand
  const { spansTarget } = parseNotes(pair.notes)

  let badge: PrimerBadge
  if (pair.specificity_hits > 1) {
    // Off-target risk — more than one product (§5.1).
    badge = { key: 'offtarget', label: 'Off-target risk', tone: 'err' }
  } else if (pair.specificity_hits <= 0) {
    // hgPcr-quirk: 0 hits ⇒ validate orientation, not silently "not specific".
    badge = { key: 'orientation', label: 'Check orientation', tone: 'warn' }
  } else if (thermoFlag) {
    // Single specific hit, but a thermodynamic concern (§5.1).
    badge = { key: 'thermo', label: 'Thermo warning', tone: 'warn' }
  } else if (spansTarget === false) {
    // Single clean hit but notes explicitly say it does not span the target —
    // closest defined bucket is the orientation/positioning concern (§5.1).
    badge = { key: 'orientation', label: 'Check orientation', tone: 'warn' }
  } else {
    // Single specific hit, no thermo flag, not explicitly off-target (§5.1).
    badge = { key: 'specific', label: 'Specific', tone: 'teal' }
  }

  return { badge, deltaTm, deltaTmWarn, gcOutOfBand, thermoFlag, spansTarget }
}

const PROVIDER_RE =
  /\b(?:provider|screen(?:ed)?\s+by|using)\s*[:=]?\s*(template|ucsc[_ -]?ispcr|ispcr|primer-?blast)\b/i
const PRODUCT_RE =
  /\b(?:products?|amplicons?)\b[^.;]*?(\d[\d,\s/]*(?:\s*bp)?(?:\s*[,/]\s*\d[\d,\s/]*\s*bp)*)/i
const SPAN_NEG_RE =
  /\b(?:does(?:\s+not|n['’]t)\s+(?:span|flank)|not\s+(?:spanning|flanking)|fails?\s+to\s+(?:span|flank))/i
const SPAN_POS_RE = /\b(?:span|spans|spanning|flank|flanks|flanking)\b/i
const PRIMER_BLAST_RE =
  /[^.;]*\bnot\b[^.;]*\bprimer-?blast\b[^.;]*/i

/** Never throws. Always returns `{ raw }`; fills fields it can match. */
export function parseNotes(notes: string | undefined | null): ParsedNotes {
  const raw = typeof notes === 'string' ? notes : ''
  if (!raw) return { raw }

  const provider = PROVIDER_RE.exec(raw)?.[1]?.toLowerCase()
  const productSizes = PRODUCT_RE.exec(raw)?.[1]?.trim()
  const primerBlastCaveat = PRIMER_BLAST_RE.exec(raw)?.[0]?.trim()

  let spansTarget: boolean | undefined
  if (SPAN_NEG_RE.test(raw)) spansTarget = false
  else if (SPAN_POS_RE.test(raw)) spansTarget = true

  return { provider, productSizes, spansTarget, primerBlastCaveat, raw }
}
