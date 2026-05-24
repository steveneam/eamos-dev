import type { GeneWindowData, WindowSegment } from './gene-window'

export const MAX_ALIGNMENT_BASES = 1500

const GAP_PENALTY = -2
const MATCH_SCORE = 2
const MISMATCH_SCORE = -1

export type AlignmentMethod = 'local' | 'positional'
export type AlignmentCellKind = 'match' | 'mismatch' | 'gap'
export type AlignmentField = 'reference' | 'edited'
export type TargetAlignmentState = 'outside' | 'match' | 'mismatch' | 'gap'

export interface SequenceParseResult {
  sequence: string
  invalidCharacters: string[]
  errors: string[]
}

export interface AlignmentIssue {
  field: AlignmentField
  message: string
}

export interface AlignmentCell {
  referenceBase: string
  editedBase: string
  referenceIndex: number | null
  editedIndex: number | null
  kind: AlignmentCellKind
  mark: '|' | '.' | ' '
  isTarget: boolean
}

export interface AlignmentDifference {
  referenceIndex: number | null
  editedIndex: number | null
  referenceBase: string
  editedBase: string
  kind: AlignmentCellKind
}

export interface TargetAlignment {
  referenceIndex: number | null
  editedIndex: number | null
  state: TargetAlignmentState
  referenceBase?: string
  editedBase?: string
}

export interface PairwiseAlignment {
  method: AlignmentMethod
  score: number
  cells: AlignmentCell[]
  matches: number
  mismatches: number
  gaps: number
  alignedLength: number
  identity: number
  referenceStart: number
  referenceEnd: number
  editedStart: number
  editedEnd: number
  differences: AlignmentDifference[]
  target: TargetAlignment
}

export interface AlignmentComparison {
  reference: SequenceParseResult
  edited: SequenceParseResult
  issues: AlignmentIssue[]
  alignment: PairwiseAlignment | null
}

export interface AlignmentSeed {
  reference: string
  edited: string
  targetReferenceIndex: number | null
  targetLabel: string
}

export type TraceBase = 'A' | 'C' | 'G' | 'T'

export interface AlignApiTraceChannel {
  base: TraceBase
  values: number[]
}

export interface AlignApiResponseShape {
  reference?: string | null
  sanger_read?: string | null
  match_line?: string | null
  mismatch_positions?: number[] | null
  target_position?: number | null
  trace_channels?: AlignApiTraceChannel[] | null
  base_calls?: string[] | null
  q_scores?: number[] | null
}

export interface TraceBaseCall {
  index: number
  base: string
  referenceBase: string | null
  qScore: number | null
  isMismatch: boolean
  isTarget: boolean
}

export interface AlignTraceView {
  reference: string
  read: string
  matchLine: string
  mismatchPositions: number[]
  targetPosition: number | null
  traceChannels: AlignApiTraceChannel[]
  baseCalls: TraceBaseCall[]
  warnings: string[]
  hasTrace: boolean
}

export function parseSequenceInput(raw: string, label: string): SequenceParseResult {
  const bases: string[] = []
  const invalid = new Set<string>()

  raw.split(/\r?\n/).forEach((line) => {
    if (line.trimStart().startsWith('>')) return

    for (const ch of line) {
      if (/\s/.test(ch) || /\d/.test(ch)) continue

      const upper = ch.toUpperCase()
      if (upper === 'U') {
        bases.push('T')
      } else if (upper === 'A' || upper === 'C' || upper === 'G' || upper === 'T' || upper === 'N') {
        bases.push(upper)
      } else {
        invalid.add(ch)
      }
    }
  })

  const sequence = bases.join('')
  const invalidCharacters = Array.from(invalid).sort()
  const errors: string[] = []

  if (sequence.length === 0) {
    errors.push(`${label} is empty.`)
  }
  if (invalidCharacters.length > 0) {
    errors.push(`${label} contains unsupported characters: ${invalidCharacters.join(' ')}.`)
  }
  if (sequence.length > MAX_ALIGNMENT_BASES) {
    errors.push(
      `${label} is ${sequence.length} bp; the browser aligner limit is ${MAX_ALIGNMENT_BASES} bp.`,
    )
  }

  return { sequence, invalidCharacters, errors }
}

export function normalizeAlignResponse(response: AlignApiResponseShape): AlignTraceView {
  const referenceParsed = parseSequenceInput(response.reference ?? '', 'Alignment reference')
  const readParsed = parseSequenceInput(response.sanger_read ?? '', 'Sanger read')
  const reference = referenceParsed.sequence
  const read = readParsed.sequence
  const warnings = [...referenceParsed.errors, ...readParsed.errors]
  const targetPosition = normalizeTargetPosition(response.target_position)
  const mismatchPositions = normalizeIndexList(response.mismatch_positions)
  const traceChannels = normalizeTraceChannels(response.trace_channels)
  const responseBaseCalls = response.base_calls ?? []
  const baseCallStrings =
    responseBaseCalls.length > 0 ? responseBaseCalls.map(normalizeBaseCall) : read.split('')
  const qScores = normalizeQScores(response.q_scores)
  const coordinateLength = Math.max(reference.length, read.length, baseCallStrings.length)

  if (targetPosition === null) {
    warnings.push('Alignment response did not include target_position.')
  } else if (targetPosition >= coordinateLength) {
    warnings.push('Alignment response target_position is outside the returned read.')
  }
  if (traceChannels.length === 0) {
    warnings.push('Alignment response did not include trace channel values.')
  }
  if (responseBaseCalls.length === 0 && read.length > 0) {
    warnings.push('Alignment response omitted base_calls; using sanger_read for display.')
  }
  if (baseCallStrings.length === 0) {
    warnings.push('Alignment response did not include base calls.')
  }
  if (qScores.length > 0 && qScores.length !== baseCallStrings.length) {
    warnings.push('Alignment response q_scores length does not match base_calls length.')
  }

  const mismatchSet = new Set(mismatchPositions)
  const baseCalls = baseCallStrings.map((base, index) => {
    const referenceBase = reference[index] ?? null
    const differsFromReference =
      referenceBase !== null && base !== 'N' && referenceBase !== 'N' && base !== referenceBase

    return {
      index,
      base,
      referenceBase,
      qScore: qScores[index] ?? null,
      isMismatch: mismatchSet.has(index) || differsFromReference,
      isTarget: targetPosition === index,
    }
  })

  return {
    reference,
    read,
    matchLine: response.match_line ?? '',
    mismatchPositions,
    targetPosition,
    traceChannels,
    baseCalls,
    warnings: Array.from(new Set(warnings)),
    hasTrace: traceChannels.some((channel) => channel.values.length > 0),
  }
}

export function compareSequences(
  referenceInput: string,
  editedInput: string,
  targetReferenceIndex: number | null = null,
): AlignmentComparison {
  const reference = parseSequenceInput(referenceInput, 'Reference sequence')
  const edited = parseSequenceInput(editedInput, 'Edited/read sequence')
  const issues: AlignmentIssue[] = [
    ...reference.errors.map((message) => ({ field: 'reference' as const, message })),
    ...edited.errors.map((message) => ({ field: 'edited' as const, message })),
  ]

  if (issues.length > 0) {
    return { reference, edited, issues, alignment: null }
  }

  return {
    reference,
    edited,
    issues,
    alignment: alignSequences(reference.sequence, edited.sequence, targetReferenceIndex),
  }
}

export function alignSequences(
  reference: string,
  edited: string,
  targetReferenceIndex: number | null = null,
): PairwiseAlignment {
  if (reference.length === edited.length) {
    return summarizeAlignment(
      'positional',
      0,
      buildPositionalCells(reference, edited, targetReferenceIndex),
      targetReferenceIndex,
    )
  }

  const local = smithWaterman(reference, edited, targetReferenceIndex)
  if (local.score > 0 && local.cells.length > 0) return local

  return summarizeAlignment(
    'positional',
    0,
    buildPositionalCells(reference, edited, targetReferenceIndex),
    targetReferenceIndex,
  )
}

export function makeAlignmentSeed(data: GeneWindowData): AlignmentSeed {
  const targetReferenceIndex = targetIndexFromWindow(data)
  const referenceFromWindow = sequenceFromWindow(data.windowSegments)
  const reference = replaceBase(referenceFromWindow, targetReferenceIndex, data.queriedVariant.refBase)
  const edited = replaceBase(referenceFromWindow, targetReferenceIndex, data.queriedVariant.altBase)

  return {
    reference,
    edited,
    targetReferenceIndex,
    targetLabel: data.queriedVariant.hgvsC,
  }
}

function sequenceFromWindow(segments: WindowSegment[]): string {
  return segments
    .map((segment) => {
      if (segment.kind === 'exon') return segment.seq
      return `${segment.fiveSeq}${segment.threeSeq}`
    })
    .join('')
    .toUpperCase()
}

function targetIndexFromWindow(data: GeneWindowData): number | null {
  let offset = 0
  const targetCds = data.queriedVariant.cdsPos

  for (const segment of data.windowSegments) {
    if (segment.kind === 'exon') {
      if (targetCds >= segment.cdsStart && targetCds <= segment.cdsEnd) {
        return offset + targetCds - segment.cdsStart
      }
      offset += segment.seq.length
    } else {
      offset += segment.fiveSeq.length + segment.threeSeq.length
    }
  }

  return null
}

function replaceBase(sequence: string, index: number | null, base: string): string {
  if (index === null || index < 0 || index >= sequence.length) return sequence
  return `${sequence.slice(0, index)}${base.toUpperCase()}${sequence.slice(index + 1)}`
}

const TRACE_BASE_ORDER: TraceBase[] = ['A', 'C', 'G', 'T']

function normalizeTargetPosition(value: number | null | undefined): number | null {
  return Number.isInteger(value) && Number(value) >= 0 ? Number(value) : null
}

function normalizeIndexList(values: number[] | null | undefined): number[] {
  const seen = new Set<number>()
  const indexes: number[] = []

  for (const value of values ?? []) {
    if (!Number.isInteger(value) || value < 0 || seen.has(value)) continue
    seen.add(value)
    indexes.push(value)
  }

  return indexes
}

function normalizeTraceChannels(
  channels: AlignApiTraceChannel[] | null | undefined,
): AlignApiTraceChannel[] {
  return (channels ?? [])
    .filter((channel) => TRACE_BASE_ORDER.includes(channel.base))
    .map((channel) => ({
      base: channel.base,
      values: channel.values.filter(Number.isFinite),
    }))
    .sort(
      (left, right) =>
        TRACE_BASE_ORDER.indexOf(left.base) - TRACE_BASE_ORDER.indexOf(right.base),
    )
}

function normalizeBaseCall(base: string): string {
  const first = base.trim().toUpperCase().charAt(0)
  return first === 'A' || first === 'C' || first === 'G' || first === 'T' || first === 'N'
    ? first
    : 'N'
}

function normalizeQScores(values: number[] | null | undefined): number[] {
  return (values ?? []).filter(Number.isFinite).map((value) => Math.max(0, Math.round(value)))
}

function smithWaterman(
  reference: string,
  edited: string,
  targetReferenceIndex: number | null,
): PairwiseAlignment {
  const cols = edited.length + 1
  const scores = new Int16Array((reference.length + 1) * cols)
  const pointers = new Uint8Array((reference.length + 1) * cols)

  let bestScore = 0
  let bestI = 0
  let bestJ = 0

  for (let i = 1; i <= reference.length; i += 1) {
    for (let j = 1; j <= edited.length; j += 1) {
      const idx = i * cols + j
      const diagonal = scores[idx - cols - 1] + scoreBases(reference[i - 1], edited[j - 1])
      const up = scores[idx - cols] + GAP_PENALTY
      const left = scores[idx - 1] + GAP_PENALTY

      let score = 0
      let pointer = 0
      if (diagonal > score) {
        score = diagonal
        pointer = 1
      }
      if (up > score) {
        score = up
        pointer = 2
      }
      if (left > score) {
        score = left
        pointer = 3
      }

      scores[idx] = score
      pointers[idx] = pointer

      if (score > bestScore) {
        bestScore = score
        bestI = i
        bestJ = j
      }
    }
  }

  const cells: AlignmentCell[] = []
  let i = bestI
  let j = bestJ

  while (i > 0 || j > 0) {
    const idx = i * cols + j
    const pointer = pointers[idx]
    if (pointer === 0 || scores[idx] === 0) break

    if (pointer === 1) {
      i -= 1
      j -= 1
      cells.push(makeCell(reference[i], edited[j], i, j, targetReferenceIndex))
    } else if (pointer === 2) {
      i -= 1
      cells.push(makeCell(reference[i], '-', i, null, targetReferenceIndex))
    } else {
      j -= 1
      cells.push(makeCell('-', edited[j], null, j, targetReferenceIndex))
    }
  }

  cells.reverse()
  return summarizeAlignment('local', bestScore, cells, targetReferenceIndex)
}

function scoreBases(referenceBase: string, editedBase: string): number {
  if (referenceBase === editedBase) return MATCH_SCORE
  return MISMATCH_SCORE
}

function buildPositionalCells(
  reference: string,
  edited: string,
  targetReferenceIndex: number | null,
): AlignmentCell[] {
  const length = Math.max(reference.length, edited.length)
  const cells: AlignmentCell[] = []

  for (let i = 0; i < length; i += 1) {
    const referenceBase = reference[i] ?? '-'
    const editedBase = edited[i] ?? '-'
    cells.push(
      makeCell(
        referenceBase,
        editedBase,
        i < reference.length ? i : null,
        i < edited.length ? i : null,
        targetReferenceIndex,
      ),
    )
  }

  return cells
}

function makeCell(
  referenceBase: string,
  editedBase: string,
  referenceIndex: number | null,
  editedIndex: number | null,
  targetReferenceIndex: number | null,
): AlignmentCell {
  const gap = referenceBase === '-' || editedBase === '-'
  const match = !gap && referenceBase === editedBase
  const kind: AlignmentCellKind = gap ? 'gap' : match ? 'match' : 'mismatch'
  const mark = kind === 'match' ? '|' : kind === 'mismatch' ? '.' : ' '

  return {
    referenceBase,
    editedBase,
    referenceIndex,
    editedIndex,
    kind,
    mark,
    isTarget: targetReferenceIndex !== null && referenceIndex === targetReferenceIndex,
  }
}

function summarizeAlignment(
  method: AlignmentMethod,
  score: number,
  cells: AlignmentCell[],
  targetReferenceIndex: number | null,
): PairwiseAlignment {
  let matches = 0
  let mismatches = 0
  let gaps = 0
  const differences: AlignmentDifference[] = []
  const referenceIndexes: number[] = []
  const editedIndexes: number[] = []
  let target: TargetAlignment = {
    referenceIndex: targetReferenceIndex,
    editedIndex: null,
    state: 'outside',
  }

  cells.forEach((cell) => {
    if (cell.referenceIndex !== null) referenceIndexes.push(cell.referenceIndex)
    if (cell.editedIndex !== null) editedIndexes.push(cell.editedIndex)

    if (cell.kind === 'match') {
      matches += 1
    } else {
      if (cell.kind === 'mismatch') mismatches += 1
      if (cell.kind === 'gap') gaps += 1
      differences.push({
        referenceIndex: cell.referenceIndex,
        editedIndex: cell.editedIndex,
        referenceBase: cell.referenceBase,
        editedBase: cell.editedBase,
        kind: cell.kind,
      })
    }

    if (cell.isTarget) {
      target = {
        referenceIndex: cell.referenceIndex,
        editedIndex: cell.editedIndex,
        state: cell.kind,
        referenceBase: cell.referenceBase,
        editedBase: cell.editedBase,
      }
    }
  })

  const alignedLength = cells.length
  return {
    method,
    score,
    cells,
    matches,
    mismatches,
    gaps,
    alignedLength,
    identity: alignedLength === 0 ? 0 : matches / alignedLength,
    referenceStart: referenceIndexes.length > 0 ? Math.min(...referenceIndexes) : 0,
    referenceEnd: referenceIndexes.length > 0 ? Math.max(...referenceIndexes) + 1 : 0,
    editedStart: editedIndexes.length > 0 ? Math.min(...editedIndexes) : 0,
    editedEnd: editedIndexes.length > 0 ? Math.max(...editedIndexes) + 1 : 0,
    differences,
    target,
  }
}
