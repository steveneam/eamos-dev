#!/usr/bin/env node
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const require = createRequire(import.meta.url)
const ts = require('../app/web/node_modules/typescript/lib/typescript.js')

const sourcePath = fileURLToPath(new URL('../app/web/lib/protein-architecture.ts', import.meta.url))
const tempDir = mkdtempSync(join(tmpdir(), 'eamos-protein-architecture-'))
const compiledPath = join(tempDir, 'protein-architecture.mjs')

try {
  const source = readFileSync(sourcePath, 'utf8')
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ES2022,
      moduleResolution: ts.ModuleResolutionKind.Bundler,
      strict: true,
    },
    fileName: sourcePath,
  }).outputText
  writeFileSync(compiledPath, compiled, 'utf8')

  const {
    canonicalizeProteinArchitectureFeature,
    collapseDuplicateProteinArchitectureFeatures,
    selectPrimaryProteinArchitectureFeatures,
  } = await import(pathToFileURL(compiledPath).href)

  const feature = (overrides) => canonicalizeProteinArchitectureFeature({
    start: 1,
    end: 1,
    label: 'Feature',
    short: 'Feature',
    kind: 'domain',
    lane: 'domains',
    ...overrides,
  })

  const sevenTmHelices = [
    [1728, 1748],
    [1760, 1780],
    [1793, 1813],
    [1832, 1852],
    [1874, 1894],
  ].map(([start, end]) => feature({
    start,
    end,
    label: 'Transmembrane helix',
    short: 'TM',
    kind: 'transmembrane',
    lane: 'topology',
    description: 'transmembrane helix',
    source: 'curated source',
  }))
  const broadSevenTmDomain = feature({
    start: 1728,
    end: 1894,
    label: 'Frizzled/Smoothened membrane region',
    short: '7TM',
    kind: 'domain',
    lane: 'domains',
    description: 'Seven-transmembrane receptor region',
    source: 'adapter summary',
    architecturePriority: 50,
  })
  const sevenTmSelected = selectPrimaryProteinArchitectureFeatures([
    broadSevenTmDomain,
    ...sevenTmHelices,
  ])
  assert.equal(
    sevenTmSelected.filter((item) => item.short === '7TM').length,
    5,
    'keeps granular TM spans instead of adding a second broad 7TM architecture row',
  )
  assert.equal(
    sevenTmSelected.some((item) => item.short === '7TM' && item.lane === 'domains'),
    false,
    'drops overlapping broad domain-lane 7TM summary',
  )

  const atpaseMotif = feature({
    start: 2244,
    end: 2249,
    label: 'Essential for ATP binding and ATPase activity',
    short: 'ATPase',
    kind: 'region',
    lane: 'motifs',
    source: 'curated source',
  })
  const atpaseAdapterCopy = feature({
    start: 2244,
    end: 2249,
    label: 'Essential for ATP binding and ATPase activity',
    short: 'ATPase',
    kind: 'domain',
    lane: 'domains',
    source: 'adapter copy',
    architecturePriority: 54,
  })
  const atpaseSelected = selectPrimaryProteinArchitectureFeatures([atpaseAdapterCopy, atpaseMotif])
  assert.deepEqual(
    atpaseSelected.map((item) => [item.short, item.lane, item.kind, item.start, item.end]),
    [['ATPase', 'motifs', 'region', 2244, 2249]],
    'keeps one ATPase feature when identical source/adapted copies cross lanes',
  )

  const nonOverlappingSameIdentity = collapseDuplicateProteinArchitectureFeatures([
    feature({ start: 10, end: 30, label: 'Repeat', short: 'REP', kind: 'repeat', lane: 'domains' }),
    feature({ start: 100, end: 130, label: 'Repeat', short: 'REP', kind: 'repeat', lane: 'domains' }),
  ])
  assert.equal(
    nonOverlappingSameIdentity.length,
    2,
    'does not collapse repeated architecture labels when spans do not overlap',
  )

  console.log('protein architecture regression: ok')
} finally {
  rmSync(tempDir, { recursive: true, force: true })
}
