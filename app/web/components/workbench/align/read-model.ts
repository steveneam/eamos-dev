/* ───────────────────────────────────────────────────────────────────────
   Align v2 read/reference model.

   A reference (template) plus N reads. Each read is a Sanger `.ab1` trace
   (parsed client-side) or a pasted sequence, aligned to the reference with the
   existing client-side engine (`compareSequences`) — no new alignment math.
─────────────────────────────────────────────────────────────────────── */

import {
  compareSequences,
  makeAlignmentSeed,
  parseSequenceInput,
  type AlignmentComparison,
} from '@/lib/workbench/alignment-pairwise'
import { COMPLEMENT, type GeneWindowData } from '@/lib/workbench/gene-window'
import { parseAbif, type AbifChannel, type TraceBase } from './abif-parser'

export interface ReadTraceBase {
  base: string
  qScore: number | null
  /** Peak sample index (PLOC), used to place the base under its trace peak. */
  peak: number
}

export interface ReadTrace {
  channels: AbifChannel[]
  baseCalls: ReadTraceBase[]
  sampleCount: number
}

export type ReadOrientation = 'forward' | 'reverse'

export interface ReadEntry {
  id: string
  label: string
  source: 'ab1' | 'paste'
  /** Forward-orientation sequence as read from the file/paste. */
  sequence: string
  /** Forward-orientation trace (AB1 only). */
  trace: ReadTrace | null
  orientation: ReadOrientation
}

export interface ReferenceState {
  label: string
  sequence: string
  /** gene · transcript · region — only when from a loaded variant context. */
  provenance: string | null
  /** Queried-variant column to highlight — only from a loaded variant context. */
  targetIndex: number | null
  custom: boolean
}

const COMPLEMENT_BASE: Record<TraceBase, TraceBase> = { A: 'T', T: 'A', C: 'G', G: 'C' }

export function defaultReference(data: GeneWindowData): ReferenceState {
  const seed = makeAlignmentSeed(data)
  const coords = data.genomicCoords
  const region =
    coords && coords.start && coords.end
      ? `${coords.chrom}:${coords.start.toLocaleString()}–${coords.end.toLocaleString()} (${coords.strand})`
      : coords?.chrom ?? ''
  const provenance = [data.gene, data.transcript, region].filter(Boolean).join(' · ')
  return {
    label: `${data.gene} reference window`,
    sequence: seed.reference,
    provenance: provenance || null,
    targetIndex: seed.targetReferenceIndex,
    custom: false,
  }
}

export function customReference(text: string, label = 'Custom reference'): ReferenceState {
  const parsed = parseSequenceInput(text, 'Reference sequence')
  if (parsed.errors.length > 0) throw new Error(parsed.errors[0])
  return { label, sequence: parsed.sequence, provenance: null, targetIndex: null, custom: true }
}

export async function readFromFile(file: File): Promise<ReadEntry> {
  const parsed = parseAbif(await file.arrayBuffer())
  return {
    id: `${file.name}-${file.size}-${file.lastModified}`,
    label: file.name,
    source: 'ab1',
    sequence: parsed.sequence,
    trace: {
      channels: parsed.channels,
      baseCalls: parsed.baseCalls.map((base, index) => ({
        base,
        qScore: parsed.qScores[index] ?? null,
        peak: parsed.peakLocations[index] ?? index,
      })),
      sampleCount: parsed.sampleCount,
    },
    orientation: 'forward',
  }
}

export function readFromPaste(text: string, label = 'Pasted read'): ReadEntry {
  const parsed = parseSequenceInput(text, 'Read sequence')
  if (parsed.errors.length > 0) throw new Error(parsed.errors[0])
  return {
    id: `paste-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    label,
    source: 'paste',
    sequence: parsed.sequence,
    trace: null,
    orientation: 'forward',
  }
}

export function reverseComplementSequence(seq: string): string {
  let out = ''
  for (let i = seq.length - 1; i >= 0; i -= 1) {
    out += COMPLEMENT[seq[i]] ?? 'N'
  }
  return out
}

/** Reverse-complement a trace: each output base's channel is the input
 *  complement channel, reversed; base calls reverse + complement; peaks mirror. */
export function reverseComplementTrace(trace: ReadTrace): ReadTrace {
  const last = trace.sampleCount - 1
  const byBase = new Map(trace.channels.map((channel) => [channel.base, channel.values]))
  const channels: AbifChannel[] = (['A', 'C', 'G', 'T'] as TraceBase[])
    .map((base) => {
      const source = byBase.get(COMPLEMENT_BASE[base]) ?? []
      return { base, values: source.slice().reverse() }
    })
    .filter((channel) => channel.values.length > 0)
  const baseCalls: ReadTraceBase[] = trace.baseCalls
    .slice()
    .reverse()
    .map((call) => ({
      base: COMPLEMENT[call.base] ?? 'N',
      qScore: call.qScore,
      peak: last - call.peak,
    }))
  return { channels, baseCalls, sampleCount: trace.sampleCount }
}

/** Find a nucleotide motif in the reference (forward + reverse-complement).
 *  Returns match start positions (reference coordinates), sorted. */
export function findMotif(reference: string, rawQuery: string): { start: number; length: number }[] {
  const ref = reference.toUpperCase()
  const query = rawQuery.toUpperCase().replace(/[^ACGTN]/g, '')
  if (query.length < 2) return []
  const patterns = new Set([query, reverseComplementSequence(query)])
  const hits: { start: number; length: number }[] = []
  for (const pattern of patterns) {
    let idx = ref.indexOf(pattern)
    while (idx !== -1) {
      hits.push({ start: idx, length: pattern.length })
      idx = ref.indexOf(pattern, idx + 1)
    }
  }
  return hits.sort((a, b) => a.start - b.start)
}

export function orientedSequence(read: ReadEntry): string {
  return read.orientation === 'reverse' ? reverseComplementSequence(read.sequence) : read.sequence
}

export function orientedTrace(read: ReadEntry): ReadTrace | null {
  if (!read.trace) return null
  return read.orientation === 'reverse' ? reverseComplementTrace(read.trace) : read.trace
}

export function alignRead(reference: ReferenceState, read: ReadEntry): AlignmentComparison {
  return compareSequences(reference.sequence, orientedSequence(read), reference.targetIndex)
}

/** Read-base indices (into the oriented read) that don't match the reference. */
export function mismatchReadIndices(comparison: AlignmentComparison): Set<number> {
  const indices = new Set<number>()
  const cells = comparison.alignment?.cells ?? []
  for (const cell of cells) {
    if (cell.kind !== 'match' && cell.editedIndex !== null) indices.add(cell.editedIndex)
  }
  return indices
}

// ─── Quality-aware analysis (Phred trim · noise flagging · het peaks) ──────

export const QUALITY_THRESHOLD = 20
const TRIM_WINDOW = 10
// Heterozygous call: a clear codominant secondary peak (≥ half the primary) at a
// good-quality base sitting well above the noise floor. Conservative on purpose —
// real het sites are rare; loose thresholds flood noisy reads with false positives.
const HET_RATIO = 0.5
const HET_MIN_PRIMARY_FRACTION = 0.2

/** Trim noisy low-Phred ends with a sliding-window mean-Q ≥ threshold rule. */
export function qualityTrim(baseCalls: ReadTraceBase[]): { start: number; end: number } {
  const n = baseCalls.length
  const q = baseCalls.map((call) => call.qScore)
  if (n === 0 || q.every((value) => value === null)) return { start: 0, end: n }
  const meanFrom = (from: number) => {
    let sum = 0
    let count = 0
    for (let i = from; i < Math.min(n, from + TRIM_WINDOW); i += 1) {
      const value = q[i]
      if (value !== null) {
        sum += value
        count += 1
      }
    }
    return count ? sum / count : 0
  }
  const meanBefore = (to: number) => {
    let sum = 0
    let count = 0
    for (let i = Math.max(0, to - TRIM_WINDOW); i < to; i += 1) {
      const value = q[i]
      if (value !== null) {
        sum += value
        count += 1
      }
    }
    return count ? sum / count : 0
  }
  let start = 0
  while (start < n && meanFrom(start) < QUALITY_THRESHOLD) start += 1
  let end = n
  while (end > start && meanBefore(end) < QUALITY_THRESHOLD) end -= 1
  return end <= start ? { start: 0, end: n } : { start, end }
}

/** Base indices with a clear codominant secondary peak at a good-quality base. */
export function detectHetIndices(trace: ReadTrace): Set<number> {
  const het = new Set<number>()
  const channels = new Map(trace.channels.map((channel) => [channel.base, channel.values]))
  let traceMax = 1
  for (const channel of trace.channels) {
    for (const value of channel.values) if (value > traceMax) traceMax = value
  }
  const minPrimary = traceMax * HET_MIN_PRIMARY_FRACTION
  trace.baseCalls.forEach((call, index) => {
    if (call.qScore !== null && call.qScore < QUALITY_THRESHOLD) return
    const sample = call.peak
    let primary = 0
    let secondary = 0
    for (const base of ['A', 'C', 'G', 'T'] as TraceBase[]) {
      const value = channels.get(base)?.[sample] ?? 0
      if (base === call.base) primary = value
      else if (value > secondary) secondary = value
    }
    if (primary >= minPrimary && secondary / primary >= HET_RATIO) het.add(index)
  })
  return het
}

/** Pick the orientation that aligns better to the reference (auto-orient). */
export function bestOrientation(reference: ReferenceState, read: ReadEntry): ReadOrientation {
  const score = (orientation: ReadOrientation) => {
    const seq = orientation === 'reverse' ? reverseComplementSequence(read.sequence) : read.sequence
    const alignment = compareSequences(reference.sequence, seq, reference.targetIndex).alignment
    return alignment ? alignment.identity * alignment.matches : 0
  }
  return score('reverse') > score('forward') ? 'reverse' : 'forward'
}

export interface ReadAnalysis {
  comparison: AlignmentComparison
  trace: ReadTrace | null
  trimStart: number
  trimEnd: number
  /** All in the oriented full-read frame (index-aligned with trace.baseCalls). */
  hetIndices: Set<number>
  realMismatch: Set<number>
  lowQMismatch: Set<number>
}

/** Align a read to the reference using its high-Q core, then classify each
 *  mismatch by Phred confidence and flag heterozygous peaks. */
export function analyzeRead(
  reference: ReferenceState,
  read: ReadEntry,
  useFullRead: boolean,
): ReadAnalysis {
  const trace = orientedTrace(read)
  const full = orientedSequence(read)
  let trimStart = 0
  let trimEnd = full.length
  if (!useFullRead && trace && trace.baseCalls.length === full.length) {
    const range = qualityTrim(trace.baseCalls)
    trimStart = range.start
    trimEnd = range.end
  }
  const core = full.slice(trimStart, trimEnd)
  const comparison = compareSequences(reference.sequence, core, reference.targetIndex)

  const realMismatch = new Set<number>()
  const lowQMismatch = new Set<number>()
  for (const cell of comparison.alignment?.cells ?? []) {
    if (cell.kind === 'match' || cell.editedIndex === null) continue
    const fullIndex = trimStart + cell.editedIndex
    const q = trace?.baseCalls[fullIndex]?.qScore ?? null
    if (q !== null && q < QUALITY_THRESHOLD) lowQMismatch.add(fullIndex)
    else realMismatch.add(fullIndex)
  }

  const hetIndices = new Set<number>()
  if (trace) {
    for (const index of detectHetIndices(trace)) {
      if (index >= trimStart && index < trimEnd) hetIndices.add(index)
    }
  }

  return { comparison, trace, trimStart, trimEnd, hetIndices, realMismatch, lowQMismatch }
}
