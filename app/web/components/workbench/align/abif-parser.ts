/* ───────────────────────────────────────────────────────────────────────
   Client-side ABIF (.ab1 / Sanger trace) parser.

   Pure DataView reader over the ABIF binary (big-endian). Extracts the same
   fields as the backend `app/backend/app/services/trace_parser.py` (Biopython)
   so a later swap to a backend trace endpoint is drop-in — see the Codex CAR
   in the Align v2 plan. No npm dependency.

   ABIF layout: 4-byte "ABIF" magic, 2-byte version, then a 28-byte root
   directory entry at offset 6 whose dataOffset points at `numElements` further
   28-byte entries. Each entry: name(4) number(i32) elementType(i16)
   elementSize(i16) numElements(i32) dataSize(i32) dataOffset(i32) handle(i32).
   When dataSize ≤ 4 the value lives inline in the dataOffset field.
─────────────────────────────────────────────────────────────────────── */

export type TraceBase = 'A' | 'C' | 'G' | 'T'

export interface AbifChannel {
  base: TraceBase
  values: number[]
}

export interface ParsedAbif {
  /** Raw called-base string (uppercased), index-aligned with peaks/qScores. */
  sequence: string
  baseCalls: string[]
  qScores: number[]
  /** Per-base peak sample index (PLOC), index-aligned with baseCalls. */
  peakLocations: number[]
  /** Processed trace channels (DATA9–12), ordered A, C, G, T. */
  channels: AbifChannel[]
  sampleCount: number
}

interface DirEntry {
  name: string
  number: number
  elementType: number
  numElements: number
  dataSize: number
  /** Absolute offset to the data (or the inline bytes when dataSize ≤ 4). */
  dataOffset: number
}

const MAX_ELEMENTS = 2_000_000

export function parseAbif(buffer: ArrayBuffer): ParsedAbif {
  const view = new DataView(buffer)
  if (view.byteLength < 34 || readAscii(view, 0, 4) !== 'ABIF') {
    throw new Error('Not an AB1/ABIF trace file (missing ABIF signature).')
  }

  const root = readDirEntry(view, 6)
  const entries = new Map<string, DirEntry>()
  for (let i = 0; i < root.numElements && i < 100_000; i += 1) {
    const entry = readDirEntry(view, root.dataOffset + i * 28)
    entries.set(`${entry.name}${entry.number}`, entry)
  }

  const raw = readChars(view, entries.get('PBAS2') ?? entries.get('PBAS1'))
  const sequence = raw.toUpperCase()
  if (!/[ACGT]/.test(sequence)) {
    throw new Error('AB1 file did not contain base calls.')
  }
  const baseCalls = sequence.split('')

  const qScores = readBytes(view, entries.get('PCON2') ?? entries.get('PCON1'))
  const peakLocations = readShorts(view, entries.get('PLOC2') ?? entries.get('PLOC1'))

  const order = (readChars(view, entries.get('FWO_1')) || 'GATC').toUpperCase()
  const dataTags = ['DATA9', 'DATA10', 'DATA11', 'DATA12']
  const byBase = new Map<TraceBase, number[]>()
  let sampleCount = 0
  for (let k = 0; k < 4; k += 1) {
    const base = order[k]
    if (base !== 'A' && base !== 'C' && base !== 'G' && base !== 'T') continue
    const values = readShorts(view, entries.get(dataTags[k]))
    if (values.length > 0) {
      byBase.set(base, values)
      sampleCount = Math.max(sampleCount, values.length)
    }
  }
  const channels: AbifChannel[] = (['A', 'C', 'G', 'T'] as TraceBase[])
    .filter((base) => byBase.has(base))
    .map((base) => ({ base, values: byBase.get(base) as number[] }))

  return { sequence, baseCalls, qScores, peakLocations, channels, sampleCount }
}

function readDirEntry(view: DataView, offset: number): DirEntry {
  const name = readAscii(view, offset, 4)
  const number = view.getInt32(offset + 4, false)
  const numElements = view.getInt32(offset + 12, false)
  const dataSize = view.getInt32(offset + 16, false)
  const inline = dataSize <= 4
  const dataOffset = inline ? offset + 20 : view.getInt32(offset + 20, false)
  return {
    name,
    number,
    elementType: view.getInt16(offset + 8, false),
    numElements,
    dataSize,
    dataOffset,
  }
}

function readAscii(view: DataView, offset: number, length: number): string {
  let out = ''
  for (let i = 0; i < length; i += 1) out += String.fromCharCode(view.getUint8(offset + i))
  return out
}

function readChars(view: DataView, entry: DirEntry | undefined): string {
  if (!entry || entry.numElements <= 0 || entry.numElements > MAX_ELEMENTS) return ''
  let out = ''
  for (let i = 0; i < entry.numElements; i += 1) {
    out += String.fromCharCode(view.getUint8(entry.dataOffset + i))
  }
  return out
}

function readBytes(view: DataView, entry: DirEntry | undefined): number[] {
  if (!entry || entry.numElements <= 0 || entry.numElements > MAX_ELEMENTS) return []
  const out: number[] = []
  for (let i = 0; i < entry.numElements; i += 1) out.push(view.getUint8(entry.dataOffset + i))
  return out
}

function readShorts(view: DataView, entry: DirEntry | undefined): number[] {
  if (!entry || entry.numElements <= 0 || entry.numElements > MAX_ELEMENTS) return []
  const out: number[] = []
  for (let i = 0; i < entry.numElements; i += 1) {
    out.push(view.getInt16(entry.dataOffset + i * 2, false))
  }
  return out
}
