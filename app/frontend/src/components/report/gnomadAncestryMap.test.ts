import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

import {
  GNOMAD_ANCESTRY_MAP_ANCHORS,
  GNOMAD_ANCESTRY_MAP_VERSION,
  gnomadMapAnchor,
} from './gnomadAncestryMap'

describe('gnomAD ancestry map anchors', () => {
  it('covers the current gnomAD group ids with deterministic anchors', () => {
    expect(Object.keys(GNOMAD_ANCESTRY_MAP_ANCHORS).sort()).toEqual([
      'afr',
      'ami',
      'amr',
      'asj',
      'eas',
      'fin',
      'mid',
      'nfe',
      'remaining',
      'rmi',
      'sas',
    ])

    for (const [groupId, anchor] of Object.entries(GNOMAD_ANCESTRY_MAP_ANCHORS)) {
      expect(anchor.x).toBeGreaterThanOrEqual(0)
      expect(anchor.x).toBeLessThanOrEqual(2000)
      expect(anchor.y).toBeGreaterThanOrEqual(0)
      expect(anchor.y).toBeLessThanOrEqual(857)
      expect(anchor.regionPath).toMatch(/^M\d/)
      expect(anchor.regionPath).toContain('Z')
      expect(anchor.context.toLowerCase()).toContain('gnomad')
      expect(anchor.context.toLowerCase()).toContain(groupId === 'remaining' ? 'rmi' : groupId)
    }
  })

  it('keeps unmapped future groups visible through the neutral fallback', () => {
    expect(gnomadMapAnchor('future_group')).toBe(GNOMAD_ANCESTRY_MAP_ANCHORS.remaining)
    expect(gnomadMapAnchor('RMI')).toBe(GNOMAD_ANCESTRY_MAP_ANCHORS.rmi)
  })

  it('keeps the Vite and Next report anchor maps in lockstep', () => {
    const viteMap = readFileSync(new URL('./gnomadAncestryMap.ts', import.meta.url), 'utf8')
    const nextMap = readFileSync(
      new URL('../../../../web/components/report/gnomadAncestryMap.ts', import.meta.url),
      'utf8',
    )

    expect(nextMap).toBe(viteMap)
    expect(GNOMAD_ANCESTRY_MAP_VERSION).toBe('eamos-gnomad-ancestry-map-v4')
  })
})
