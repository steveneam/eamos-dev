#!/usr/bin/env node
// eamos-web-boundary - structural boundary guard for the app/web Next.js surface.
//
// A node guard (no vitest harness in app/web) reusing the eamos-*.mjs idiom, run
// over GIT-TRACKED app/web files. It asserts four boundaries and signals via the
// exit code so CI and the pre-commit hook can gate on it:
//
//   1. Client/server boundary: no `'use client'` component statically imports a
//      server-only module (`next/headers` or utils/supabase/server) - that leaks
//      server code (cookies()) into the browser bundle and breaks the build.
//   2. No merge-conflict markers in tracked app/web files (CRLF-safe: exactly-7
//      markers matched at line start after stripping a trailing CR, never by
//      whole-line equality, so `=======\r` is caught and a decorative `====...`
//      run of 8+ is not).
//   3. Contract canary: the active backend.ts contract exists and is non-empty.
//      Full schema<->TypeScript parity is guarded by test_frontend_contract.py.
//   4. Free predictor catalog: no product access split returns, the complete
//      engine catalog stays visible, and REVEL + SpliceAI remain in product copy.
//   5. Landing trust contract: bundled hero identities match tracked backend
//      evidence, source states stay explained, and audited overclaims stay gone.
//   6. Analytics privacy: only explicit route-level pageviews are enabled;
//      automatic interaction, page-leave, replay, and survey capture stay off.
//
// Usage:
//   node scripts/eamos-web-boundary.mjs           # scan app/web
//   node scripts/eamos-web-boundary.mjs --json
//   node scripts/eamos-web-boundary.mjs --help
//
// Exit codes: 0 = clean, 1 = boundary violation(s), 2 = usage / git error.

import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(HERE, '..')

const argv = process.argv.slice(2)
if (argv.includes('--help') || argv.includes('-h')) {
  process.stdout.write(
    'Usage: node scripts/eamos-web-boundary.mjs [--json]\n' +
      'Structural boundary guard for app/web (client/server imports, conflict markers, contract canary).\n' +
      'Exit: 0 clean, 1 violation(s), 2 error.\n',
  )
  process.exit(0)
}
const JSON_OUT = argv.includes('--json')

// Server-only module specifiers a client component must not statically import.
const SERVER_ONLY = [/^next\/headers$/, /utils\/supabase\/server$/]
const USE_CLIENT_RE = /^['"]use client['"]\s*;?\s*$/
const IMPORT_FROM_RE = /^\s*import\b[^'"]*from\s*['"]([^'"]+)['"]/
const IMPORT_BARE_RE = /^\s*import\s*['"]([^'"]+)['"]/
// Exactly-7 conflict marker at line start, boundary = whitespace (incl. CR) or EOL.
const CONFLICT_RE = new RegExp('^(' + '<'.repeat(7) + '|' + '='.repeat(7) + '|' + '>'.repeat(7) + ')(\\s|$)')
const PREDICTOR_ACCESS_SPLIT_RE = /License review|License-gated source|Commercial-gated source|SourceAccessTag|TierTag|alphamissense_on_hold/
const PREDICTOR_ENTITLEMENT_FIELD_RE = /\b(?:public_serialization_allowed|launch_gate)\b/
const REQUIRED_PREDICTORS = [
  'AlphaMissense',
  'ESM1b',
  'REVEL',
  'PrimateAI-3D',
  'MetaLR',
  'CI-SpliceAI',
  'SpliceAI',
  'Pangolin',
  'CADD',
  'GPN-MSA',
  'CAPICE',
]

function trackedWebFiles() {
  const out = execFileSync('git', ['ls-files', 'app/web'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
  })
  return out.split(/\r?\n/).filter((f) => /\.(ts|tsx|mjs|js|jsx)$/.test(f))
}

function firstCodeLines(lines, n) {
  const out = []
  for (const raw of lines) {
    const line = raw.replace(/\r$/, '').trim()
    if (!line || line.startsWith('//') || line.startsWith('/*') || line.startsWith('*')) continue
    out.push(line)
    if (out.length >= n) break
  }
  return out
}

const violations = []

let files
try {
  files = trackedWebFiles()
} catch (err) {
  const error = err && err.message ? err.message : String(err)
  if (JSON_OUT) process.stdout.write(JSON.stringify({ status: 'error', error }, null, 2) + '\n')
  else process.stderr.write(`eamos-web-boundary: git error: ${error}\n`)
  process.exit(2)
}

for (const rel of files) {
  const abs = join(REPO_ROOT, rel)
  let text
  try {
    text = readFileSync(abs, 'utf8')
  } catch {
    continue
  }
  const lines = text.split(/\r?\n/)
  const isClient = firstCodeLines(lines, 3).some((l) => USE_CLIENT_RE.test(l))

  lines.forEach((raw, i) => {
    const line = raw.replace(/\r$/, '')
    // 2) conflict markers
    if (CONFLICT_RE.test(line)) {
      violations.push({ kind: 'conflict-marker', file: rel, line: i + 1, detail: line.slice(0, 40) })
    }
    // 4a) one free predictor catalog: no access-tier vocabulary or client-side
    // entitlement field belongs on active app/components surfaces.
    if (PREDICTOR_ACCESS_SPLIT_RE.test(line)) {
      violations.push({
        kind: 'predictor-access-split',
        file: rel,
        line: i + 1,
        detail: 'free predictor catalog must not render an access tier or license-review label',
      })
    }
    if ((rel.startsWith('app/web/app/') || rel.startsWith('app/web/components/')) && PREDICTOR_ENTITLEMENT_FIELD_RE.test(line)) {
      violations.push({
        kind: 'predictor-client-entitlement',
        file: rel,
        line: i + 1,
        detail: 'backend predictor metadata is informational and must not become a client access filter',
      })
    }
    // 1) client/server import boundary
    if (isClient) {
      const m = IMPORT_FROM_RE.exec(line) || IMPORT_BARE_RE.exec(line)
      if (m && SERVER_ONLY.some((re) => re.test(m[1]))) {
        violations.push({
          kind: 'client-imports-server',
          file: rel,
          line: i + 1,
          detail: `'use client' file imports server-only module ${m[1]}`,
        })
      }
    }
  })
}

// 3) active contract canary
for (const rel of ['app/web/lib/backend.ts']) {
  const abs = join(REPO_ROOT, rel)
  if (!existsSync(abs) || readFileSync(abs, 'utf8').trim().length === 0) {
    violations.push({ kind: 'missing-contract', file: rel, line: 0, detail: 'active contract missing or empty' })
  }
}

// 4b) the full catalog remains a visible, free product contract.
const predictorTableRel = 'app/web/components/report/CalibratedInSilicoTable.tsx'
const predictorTablePath = join(REPO_ROOT, predictorTableRel)
if (!existsSync(predictorTablePath)) {
  violations.push({ kind: 'missing-predictor-catalog', file: predictorTableRel, line: 0, detail: 'predictor catalog missing' })
} else {
  const predictorTable = readFileSync(predictorTablePath, 'utf8')
  for (const predictor of REQUIRED_PREDICTORS) {
    if (!predictorTable.includes(`name: '${predictor}'`)) {
      violations.push({
        kind: 'missing-free-predictor',
        file: predictorTableRel,
        line: 0,
        detail: `${predictor} missing from the free predictor catalog`,
      })
    }
  }
}

const marketingFiles = [
  'app/web/components/auth/AuthPageClient.tsx',
  'app/web/components/landing/Faq.tsx',
  'app/web/components/landing/HowItWorks.tsx',
  'app/web/lib/sources.ts',
]
const marketingText = marketingFiles
  .filter((rel) => existsSync(join(REPO_ROOT, rel)))
  .map((rel) => readFileSync(join(REPO_ROOT, rel), 'utf8'))
  .join('\n')
for (const predictor of REQUIRED_PREDICTORS) {
  if (!marketingText.includes(predictor)) {
    violations.push({
      kind: 'missing-predictor-marketing',
      file: marketingFiles.join(', '),
      line: 0,
      detail: `${predictor} missing from the visible free-product catalog copy`,
    })
  }
}

// 5a) The landing may promise traceability and visible uncertainty, but not
// universal variant coverage, measured time savings, or clinical outcomes.
const landingTrustFiles = [
  'app/web/components/landing/LandingClient.tsx',
  'app/web/components/landing/LandingNav.tsx',
  'app/web/components/landing/HeroVariantMap.tsx',
  'app/web/components/landing/HowItWorks.tsx',
  'app/web/components/landing/MetricBelt.tsx',
  'app/web/components/landing/Testimonials.tsx',
  'app/web/components/landing/Faq.tsx',
  'app/web/components/landing/SiteFooter.tsx',
]
const landingTrustText = landingTrustFiles
  .filter((rel) => existsSync(join(REPO_ROOT, rel)))
  .map((rel) => readFileSync(join(REPO_ROOT, rel), 'utf8'))
  .join('\n')
const retiredLandingClaims = [
  [/Understand any genetic/i, 'universal variant coverage'],
  [/countless databases/i, 'uncounted database breadth'],
  [/every second matters/i, 'clinical timing outcome'],
  [/right treatment in time/i, 'treatment outcome'],
  [/give that time back/i, 'unmeasured time saving'],
]
for (const [pattern, claim] of retiredLandingClaims) {
  if (pattern.test(landingTrustText)) {
    violations.push({
      kind: 'landing-overclaim',
      file: landingTrustFiles.join(', '),
      line: 0,
      detail: `${claim} claim returned without a reproducible artifact`,
    })
  }
}
if (/from\s+['"](?:@gsap\/react|gsap(?:\/[^'"]*)?)['"]/.test(landingTrustText)) {
  violations.push({
    kind: 'landing-performance-drift',
    file: 'app/web/components/landing/LandingNav.tsx',
    line: 0,
    detail: 'the landing nav scroll handoff must remain dependency-free',
  })
}

// 5b) The hero's bundled RPE65 identities are generated from the same tracked
// coordinate proof used by backend fixture tests, not hand-invented marketing.
const heroRel = 'app/web/components/landing/HeroVariantMap.tsx'
const heroPath = join(REPO_ROOT, heroRel)
const coordinateIndexRel = 'app/backend/app/fixtures/coordinate_index/eamos_coordinate_index_tiny.jsonl'
const coordinateIndexPath = join(REPO_ROOT, coordinateIndexRel)
if (!existsSync(heroPath) || !existsSync(coordinateIndexPath)) {
  violations.push({
    kind: 'missing-landing-trust-proof',
    file: `${heroRel}, ${coordinateIndexRel}`,
    line: 0,
    detail: 'hero or tracked coordinate proof missing',
  })
} else {
  const heroText = readFileSync(heroPath, 'utf8')
  const variant = readFileSync(coordinateIndexPath, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
    .find((record) => record.record_type === 'variant' && record.gene === 'RPE65' && record.cdna === 'c.260A>G')
  if (!variant) {
    violations.push({
      kind: 'missing-landing-trust-proof',
      file: coordinateIndexRel,
      line: 0,
      detail: 'bundled RPE65 c.260A>G coordinate proof missing',
    })
  } else {
    const position = String(variant.pos).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
    const heroFacts = [
      variant.transcript,
      `${variant.gene} ${variant.cdna}`,
      variant.protein_change,
      `chr${variant.chrom}:${position} ${variant.ref}>${variant.alt}`,
    ]
    for (const fact of heroFacts) {
      if (!heroText.includes(fact)) {
        violations.push({
          kind: 'landing-demo-identity-drift',
          file: heroRel,
          line: 0,
          detail: `${fact} no longer matches ${coordinateIndexRel}`,
        })
      }
    }
  }
}

// 5c) One compact trust note owns the runtime-state explanation. The historical
// USH2A specimen keeps only the two population facts recorded by eamos_press;
// the contradicted rarity verdict and untracked study count must stay absent.
const howRel = 'app/web/components/landing/HowItWorks.tsx'
const howText = existsSync(join(REPO_ROOT, howRel)) ? readFileSync(join(REPO_ROOT, howRel), 'utf8') : ''
for (const statePattern of [/\bLive\b/, /\bCached\b/, /Bundled\s+demo/, /\bUnavailable\b/]) {
  if (!statePattern.test(howText)) {
    violations.push({
      kind: 'missing-landing-source-state',
      file: howRel,
      line: 0,
      detail: `${statePattern} missing from the compact source-status note`,
    })
  }
}

const specimenRel = 'app/web/components/landing/MetricBelt.tsx'
const claimProofRel = 'app/backend/tests/test_claim_provenance.py'
const specimenText = existsSync(join(REPO_ROOT, specimenRel)) ? readFileSync(join(REPO_ROOT, specimenRel), 'utf8') : ''
const claimProofText = existsSync(join(REPO_ROOT, claimProofRel))
  ? readFileSync(join(REPO_ROOT, claimProofRel), 'utf8')
  : ''
for (const [renderedFact, recordedFact] of [['Max AF 0.182%', '"popmax_frequency": 0.001817'], ['AC 2,357', '"allele_count": 2357']]) {
  if (!specimenText.includes(renderedFact) || !claimProofText.includes(recordedFact)) {
    violations.push({
      kind: 'landing-specimen-proof-drift',
      file: `${specimenRel}, ${claimProofRel}`,
      line: 0,
      detail: `${renderedFact} is not paired with its executable claim-provenance fact`,
    })
  }
}
for (const retiredSpecimenClaim of ['Low Frequency', '3 Unique']) {
  if (specimenText.includes(retiredSpecimenClaim)) {
    violations.push({
      kind: 'landing-specimen-overclaim',
      file: specimenRel,
      line: 0,
      detail: `${retiredSpecimenClaim} must not return to the audited USH2A snapshot`,
    })
  }
}

// 6) The route-only analytics claim is an executable client boundary. Automatic
// capture can include rendered variant text or a full query URL, so every
// implicit PostHog channel stays disabled until a separately reviewed event is
// instrumented with content-free properties.
const providersRel = 'app/web/app/providers.tsx'
const providersText = existsSync(join(REPO_ROOT, providersRel))
  ? readFileSync(join(REPO_ROOT, providersRel), 'utf8')
  : ''
const requiredAnalyticsGuards = [
  [/capture_pageleave:\s*false/, 'automatic page-leave capture'],
  [/autocapture:\s*false/, 'automatic interaction capture'],
  [/disable_session_recording:\s*true/, 'session recording'],
  [/disable_surveys:\s*true/, 'survey extension loading'],
  [/\$current_url:\s*window\.location\.origin\s*\+\s*pathname/, 'route-only pageview URL'],
]
for (const [pattern, boundary] of requiredAnalyticsGuards) {
  if (!pattern.test(providersText)) {
    violations.push({
      kind: 'analytics-privacy-drift',
      file: providersRel,
      line: 0,
      detail: `${boundary} no longer preserves the route-only analytics contract`,
    })
  }
}

if (JSON_OUT) {
  process.stdout.write(
    JSON.stringify({ status: violations.length ? 'failed' : 'ok', violations }, null, 2) + '\n',
  )
} else if (violations.length === 0) {
  process.stdout.write(`eamos-web-boundary: clean - ${files.length} tracked app/web files, no boundary violations.\n`)
} else {
  process.stderr.write(`eamos-web-boundary: ${violations.length} violation(s):\n`)
  for (const v of violations) process.stderr.write(`  [${v.kind}] ${v.file}:${v.line}: ${v.detail}\n`)
}

process.exit(violations.length ? 1 : 0)
