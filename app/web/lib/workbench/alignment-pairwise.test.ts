import { describe, expect, it } from 'vitest'
import {
  alignSequences,
  compareSequences,
  normalizeAlignResponse,
  parseSequenceInput,
} from './alignment-pairwise'

describe('parseSequenceInput', () => {
  it('accepts FASTA, whitespace, line numbers, and RNA U bases', () => {
    const parsed = parseSequenceInput(
      '>read 1\nacgu acgt\n12 nn\n',
      'Edited/read sequence',
    )

    expect(parsed.sequence).toBe('ACGTACGTNN')
    expect(parsed.errors).toEqual([])
  })

  it('reports unsupported characters without dropping valid bases', () => {
    const parsed = parseSequenceInput('ACGT?X', 'Reference sequence')

    expect(parsed.sequence).toBe('ACGT')
    expect(parsed.invalidCharacters).toEqual(['?', 'X'])
    expect(parsed.errors[0]).toMatch(/unsupported characters/)
  })
})

describe('alignSequences', () => {
  it('uses positional comparison for equal-length edited sequences', () => {
    const alignment = alignSequences('ACGTA', 'ACGGA', 3)

    expect(alignment.method).toBe('positional')
    expect(alignment.matches).toBe(4)
    expect(alignment.mismatches).toBe(1)
    expect(alignment.gaps).toBe(0)
    expect(alignment.target.state).toBe('mismatch')
    expect(alignment.target.referenceBase).toBe('T')
    expect(alignment.target.editedBase).toBe('G')
  })

  it('locally aligns a pasted read within a longer reference', () => {
    const alignment = alignSequences('TTTAAACCCGGGTTT', 'AAACCCAGG', 9)

    expect(alignment.method).toBe('local')
    expect(alignment.referenceStart).toBe(3)
    expect(alignment.referenceEnd).toBe(12)
    expect(alignment.editedStart).toBe(0)
    expect(alignment.editedEnd).toBe(9)
    expect(alignment.mismatches).toBe(1)
    expect(alignment.target.state).toBe('mismatch')
    expect(alignment.target.referenceBase).toBe('G')
    expect(alignment.target.editedBase).toBe('A')
  })

  it('keeps deterministic gap calls for simple deletions', () => {
    const alignment = alignSequences('ACGTACGT', 'ACGACGT', 3)

    expect(alignment.method).toBe('local')
    expect(alignment.gaps).toBe(1)
    expect(alignment.target.state).toBe('gap')
    expect(alignment.target.referenceBase).toBe('T')
    expect(alignment.target.editedBase).toBe('-')
  })

  it('falls back to positional comparison when no local match scores above zero', () => {
    const alignment = alignSequences('AAAA', 'TTTT', 1)

    expect(alignment.method).toBe('positional')
    expect(alignment.matches).toBe(0)
    expect(alignment.mismatches).toBe(4)
    expect(alignment.target.state).toBe('mismatch')
  })
})

describe('compareSequences', () => {
  it('does not align invalid input', () => {
    const comparison = compareSequences('ACGT', 'AC?T', 1)

    expect(comparison.alignment).toBeNull()
    expect(comparison.issues).toHaveLength(1)
    expect(comparison.issues[0].field).toBe('edited')
  })
})

describe('normalizeAlignResponse', () => {
  it('prepares trace channels, base calls, Q scores, and target annotation', () => {
    const trace = normalizeAlignResponse({
      reference: 'ACGTA',
      sanger_read: 'ACGGA',
      match_line: '||| |',
      mismatch_positions: [3],
      target_position: 3,
      trace_channels: [
        { base: 'G', values: [0, 0.5, 1] },
        { base: 'A', values: [1, 0.5, 0] },
      ],
      base_calls: ['A', 'C', 'G', 'G', 'A'],
      q_scores: [38, 39, 40, 24, 37],
    })

    expect(trace.reference).toBe('ACGTA')
    expect(trace.read).toBe('ACGGA')
    expect(trace.hasTrace).toBe(true)
    expect(trace.traceChannels.map((channel) => channel.base)).toEqual(['A', 'G'])
    expect(trace.baseCalls[3]).toEqual({
      index: 3,
      base: 'G',
      referenceBase: 'T',
      qScore: 24,
      isMismatch: true,
      isTarget: true,
    })
    expect(trace.warnings).toEqual([])
  })

  it('reports response gaps while keeping a displayable read fallback', () => {
    const trace = normalizeAlignResponse({
      reference: 'ACGT',
      sanger_read: 'ACGA',
      target_position: 9,
      q_scores: [30],
    })

    expect(trace.baseCalls.map((call) => call.base).join('')).toBe('ACGA')
    expect(trace.hasTrace).toBe(false)
    expect(trace.warnings).toContain(
      'Alignment response target_position is outside the returned read.',
    )
    expect(trace.warnings).toContain('Alignment response did not include trace channel values.')
    expect(trace.warnings).toContain(
      'Alignment response omitted base_calls; using sanger_read for display.',
    )
    expect(trace.warnings).toContain(
      'Alignment response q_scores length does not match base_calls length.',
    )
  })
})
