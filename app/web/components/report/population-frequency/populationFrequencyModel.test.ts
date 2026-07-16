import { describe, expect, it } from 'vitest'

import type { PopulationFrequencyVisualGroup } from '@/lib/backend'

import {
  applyDatasetToGroup,
  applyDatasetToOverall,
  bandForAf,
  buildAncestryFrequencyTsv,
  formatFrequency,
  selectDatasetCell,
  sourceStatusNeedsDisclosure,
  uniqueWarnings,
  warningCopy,
} from './populationFrequencyModel'

const GROUP: PopulationFrequencyVisualGroup = {
  id: 'afr',
  label: 'African/African American genetic ancestry',
  allele_frequency: 0.002,
  allele_count: 20,
  allele_number: 10_000,
  homozygote_count: 1,
  is_popmax: true,
  data_state: 'observed',
  sort_order: 1,
  exome: {
    allele_frequency: 0.001,
    allele_count: 8,
    allele_number: 8_000,
    homozygote_count: 0,
  },
  genome: {
    allele_frequency: 0,
    allele_count: 0,
    allele_number: 2_000,
    homozygote_count: 0,
  },
  warnings: [],
}

describe('population frequency dataset model', () => {
  it('selects joint, exome, genome, and empty cells without mutating the source group', () => {
    expect(selectDatasetCell(GROUP, true, true)).toEqual({
      allele_frequency: 0.002,
      allele_count: 20,
      allele_number: 10_000,
      homozygote_count: 1,
    })
    expect(selectDatasetCell(GROUP, true, false)).toEqual(GROUP.exome)
    expect(selectDatasetCell(GROUP, false, true)).toEqual(GROUP.genome)
    expect(selectDatasetCell(GROUP, false, false)).toEqual({
      allele_frequency: null,
      allele_count: null,
      allele_number: null,
      homozygote_count: null,
    })

    const exome = applyDatasetToGroup(GROUP, true, false)
    const genome = applyDatasetToGroup(GROUP, false, true)
    expect(exome).toMatchObject({ allele_frequency: 0.001, data_state: 'observed' })
    expect(genome).toMatchObject({ allele_frequency: 0, data_state: 'zero_observed' })
    expect(GROUP).toMatchObject({ allele_frequency: 0.002, data_state: 'observed' })
  })

  it('recomputes only the whole-cohort total because the contract has no per-dataset sex split', () => {
    const overall = {
      total: GROUP,
      xx: { allele_frequency: 0.003, allele_count: 6 },
      xy: { allele_frequency: 0.001, allele_count: 2 },
    }
    expect(applyDatasetToOverall(overall, true, false)).toEqual({
      total: { ...GROUP, ...GROUP.exome },
      xx: overall.xx,
      xy: overall.xy,
    })
  })

  it('exports raw values for the selected ancestry and overall cells', () => {
    const tsv = buildAncestryFrequencyTsv([GROUP], {
      total: GROUP,
      xx: { allele_frequency: 0.003, allele_count: 6 },
    })
    expect(tsv.split('\n')).toEqual([
      'Genetic ancestry group\tAllele frequency\tAllele count\tAllele number\tHomozygotes',
      'African/African American\t0.002\t20\t10000\t1',
      'Total\t0.002\t20\t10000\t1',
      'XX\t0.003\t6\t\t',
    ])
  })
})

describe('population frequency presentation decisions', () => {
  it('uses fixed absolute AF bands and keeps absent observations neutral', () => {
    expect(bandForAf(0.06)?.id).toBe('common')
    expect(bandForAf(0.000001)?.id).toBe('rare')
    expect(bandForAf(0, 'zero_observed')).toBeNull()
    expect(bandForAf(null)).toBeNull()
  })

  it('keeps compact number, warning, and source-status copy stable', () => {
    expect(formatFrequency(0)).toBe('0%')
    expect(formatFrequency(0.000005)).toBe('5.00e-4%')
    expect(formatFrequency(null)).toBe('Not reported')
    expect(warningCopy('allele_number_unavailable:afr')).toContain('sample size')
    expect(sourceStatusNeedsDisclosure('cache')).toBe(false)
    expect(sourceStatusNeedsDisclosure('failed')).toBe(true)
    expect(uniqueWarnings(['a', '', 'a', 'b'])).toEqual(['a', 'b'])
  })
})
