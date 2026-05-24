import { describe, expect, it } from 'vitest'
import {
  alignSequences,
  compareSequences,
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
