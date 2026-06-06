import type { AlignApiResponseShape, AlignApiTraceChannel, TraceBase } from './alignment-pairwise'

/*
   Offline `AlignApiResponseShape` sample for the Workbench Align tool.

   On-brand RPE65 c.260A>G (p.Asp87Gly): a wild-type reference window vs a Sanger
   read carrying the variant. The central GAC (Asp) codon reads GGC (Gly) at the
   target base. Used as the mock-first fallback when POST /api/v1/align is
   unreachable, mirroring PRIMER_SAMPLE / CRISPR_SAMPLE.
*/

const REFERENCE = 'ACCTGTGGACAAGACAGTCGACATTCGGTGC'
const TARGET_INDEX = 13 // the A>G base: reference 'A' (codon GAC) → read 'G' (codon GGC)
const READ = `${REFERENCE.slice(0, TARGET_INDEX)}G${REFERENCE.slice(TARGET_INDEX + 1)}`

const TRACE_BASES: TraceBase[] = ['A', 'C', 'G', 'T']
const SAMPLE_OFFSETS = [-1.5, -0.5, 0.5, 1.5] // four sample points across one base call

// Synthesize four chromatogram channels from the read: each base contributes a
// Gaussian peak in its own channel over low, flat noise elsewhere. Kept as a
// builder (not a ~500-number literal) so peaks always track the base calls.
function buildTraceChannels(read: string): AlignApiTraceChannel[] {
  return TRACE_BASES.map((channelBase) => {
    const values: number[] = []
    read.split('').forEach((base, baseIndex) => {
      const amplitude = 88 + ((baseIndex * 7) % 17) // gentle per-base variation
      SAMPLE_OFFSETS.forEach((offset, sampleIndex) => {
        const peak = Math.round(amplitude * Math.exp(-(offset * offset) / 1.6))
        const noise = 4 + ((baseIndex + sampleIndex) % 5)
        values.push(base === channelBase ? peak + noise : noise)
      })
    })
    return { base: channelBase, values }
  })
}

function buildMatchLine(reference: string, read: string): string {
  return reference
    .split('')
    .map((base, index) => (base === read[index] ? '|' : '.'))
    .join('')
}

// Clean middle, noisier ends (typical Sanger), high-confidence variant call.
function buildQScores(length: number): number[] {
  return Array.from({ length }, (_, index) => {
    if (index < 2) return 20 + index * 4
    if (index > length - 3) return 28
    return 40
  })
}

export const ALIGN_SAMPLE: AlignApiResponseShape = {
  reference: REFERENCE,
  sanger_read: READ,
  match_line: buildMatchLine(REFERENCE, READ),
  mismatch_positions: [TARGET_INDEX],
  target_position: TARGET_INDEX,
  trace_channels: buildTraceChannels(READ),
  base_calls: READ.split(''),
  q_scores: buildQScores(READ.length),
}
