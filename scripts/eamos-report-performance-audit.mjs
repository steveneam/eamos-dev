#!/usr/bin/env node
// eamos-report-performance-audit - read-only latency/payload audit for /report data paths.
//
// Examples:
//   node scripts/eamos-report-performance-audit.mjs
//   node scripts/eamos-report-performance-audit.mjs --base=https://eamos-dev-sg.onrender.com
//   node scripts/eamos-report-performance-audit.mjs --variant="ABCA4:c.5435T>A" --json
//   node scripts/eamos-report-performance-audit.mjs --runs=3 --skip-viewer --max-report-payload-bytes=750000
//   node scripts/eamos-report-performance-audit.mjs --variant="RPE65:c.271C>T" --require-ok

const DEFAULT_BASE = 'https://eamos-dev-sg.onrender.com'
const DEFAULT_VARIANTS = [
  'ABCA4:c.5435T>A',
  'ABCA4:c.5461-10T>C',
  'RPE65:c.260A>G',
  'USH2A:c.2276G>T',
]
const DEFAULT_SECTIONS = [
  'publications',
  'therapies_trials',
  'computational_deep_dive',
  'clingen_vcep',
]
const LOOKUP_TIMING_HEADER = 'x-eamos-lookup-timing'

const args = parseArgs(process.argv.slice(2))
const baseUrl = stripTrailingSlash(args.base ?? DEFAULT_BASE)
const variants = listArg(args.variant).length > 0 ? listArg(args.variant) : DEFAULT_VARIANTS
const sections = listArg(args.section).length > 0 ? listArg(args.section) : DEFAULT_SECTIONS
const timeoutMs = positiveInteger(args.timeout, 180000)
const runCount = positiveInteger(args.runs ?? args.repeat, 1)
const emitJson = flagEnabled(args.json)
const skipSections = flagEnabled(args['skip-sections'])
const skipViewer = flagEnabled(args['skip-viewer'])
const requireOk = flagEnabled(args['require-ok'])
const thresholds = {
  lookupResponseBytes: positiveIntegerOrNull(
    args['max-lookup-response-bytes'] ?? args['max-response-bytes'],
  ),
  reportPayloadBytes: positiveIntegerOrNull(args['max-report-payload-bytes']),
  sectionEnvelopeBytes: positiveIntegerOrNull(args['max-section-envelope-bytes']),
  sectionPayloadBytes: positiveIntegerOrNull(args['max-section-payload-bytes']),
}

const report = {
  tool: 'eamos-report-performance-audit',
  baseUrl,
  timeoutMs,
  runCount,
  requireOk,
  thresholds: compactThresholds(thresholds),
  generatedAt: new Date().toISOString(),
  variants: [],
  requiredEndpointFailures: [],
  violations: [],
}

for (const variantText of variants) {
  const variant = parseVariant(variantText)
  const body = { gene: variant.gene, cdna: variant.cdna, species: 'human' }
  const entry = {
    variant: `${variant.gene}:${variant.cdna}`,
    runs: [],
  }

  for (let runIndex = 0; runIndex < runCount; runIndex += 1) {
    entry.runs.push(await auditVariantRun(body, runIndex))
  }

  const firstRun = entry.runs[0]
  entry.lookup = firstRun.lookup
  entry.summary = firstRun.summary
  entry.sections = firstRun.sections
  entry.viewer = firstRun.viewer
  entry.stats = summarizeVariantRuns(entry.runs)
  if (requireOk) {
    report.requiredEndpointFailures.push(...requiredEndpointFailures(entry))
  }
  report.violations.push(...thresholdViolations(entry, thresholds))
  report.variants.push(entry)
}

if (emitJson) {
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
} else {
  printHuman(report)
}
if (report.violations.length > 0 || report.requiredEndpointFailures.length > 0) {
  process.exitCode = 1
}

async function auditVariantRun(body, runIndex) {
  const run = {
    run: runIndex + 1,
    phase: runIndex === 0 ? 'cold_or_first' : 'warm_repeat',
    lookup: await timedPost('/api/v1/lookup', body),
    summary: await timedPost('/api/v1/lookup/summary', body),
    sections: {},
    viewer: null,
  }

  if (run.lookup.ok && run.lookup.json) {
    run.lookup.payloadSizes = payloadSizes(run.lookup.json)
    run.lookup.reportFacts = reportFacts(run.lookup.json)
  }
  if (!skipSections) {
    for (const section of sections) {
      const sectionBody = { ...body, include: [section] }
      const result = await timedPost('/api/v1/lookup/sections', sectionBody)
      if (result.ok && result.json?.sections?.[section]) {
        result.sectionStatus = result.json.sections[section].status ?? null
        result.payloadSizes = {
          sectionEnvelope: jsonSize(result.json.sections[section]),
          sectionPayload: jsonSize(result.json.sections[section].payload),
        }
      }
      run.sections[section] = result
    }
  }
  if (!skipViewer) {
    run.viewer = await timedPost('/api/v1/viewer', {
      ...body,
      allele_mode: 'variant',
      window: {
        kind: 'around_variant',
        cds_flank_bp: 120,
        intron_flank_bp: 30,
      },
      tracks: ['sequence', 'exons', 'clinvar', 'protein_features', 'restriction'],
    })
  }
  return run
}

function parseArgs(values) {
  const out = {}
  for (const raw of values) {
    if (!raw.startsWith('--')) continue
    const body = raw.slice(2)
    const eq = body.indexOf('=')
    if (eq === -1) {
      out[body] = true
      continue
    }
    const key = body.slice(0, eq)
    const value = body.slice(eq + 1)
    if (out[key] == null) {
      out[key] = value
    } else if (Array.isArray(out[key])) {
      out[key].push(value)
    } else {
      out[key] = [out[key], value]
    }
  }
  return out
}

function listArg(value) {
  if (value == null) return []
  const values = Array.isArray(value) ? value : [value]
  return values
    .flatMap((item) => String(item).split(','))
    .map((item) => item.trim())
    .filter(Boolean)
}

function flagEnabled(value) {
  return value === true || value === 'true'
}

function positiveInteger(value, fallback) {
  const parsed = Number.parseInt(String(value ?? ''), 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

function positiveIntegerOrNull(value) {
  if (value == null) return null
  const parsed = Number.parseInt(String(value), 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function compactThresholds(values) {
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value != null))
}

function parseVariant(raw) {
  const text = String(raw).trim()
  const sep = text.includes(':') ? ':' : ' '
  const [geneRaw, ...rest] = text.split(sep)
  const gene = String(geneRaw ?? '').trim().toUpperCase()
  const cdna = rest.join(sep).trim()
  if (!gene || !cdna) {
    throw new Error(`Invalid --variant value "${raw}". Use GENE:c.HGVS, for example ABCA4:c.5435T>A.`)
  }
  return { gene, cdna }
}

function stripTrailingSlash(value) {
  return String(value).replace(/\/+$/, '')
}

async function timedPost(path, body) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  const started = performance.now()
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
    const text = await response.text()
    const elapsedMs = Math.round(performance.now() - started)
    const lookupTimingHeader = response.headers.get(LOOKUP_TIMING_HEADER)
    let json = null
    try {
      json = text ? JSON.parse(text) : null
    } catch {
      json = null
    }
    return {
      ok: response.ok,
      status: response.status,
      elapsedMs,
      bytes: byteSize(text),
      error: response.ok ? null : errorSummary(json, text),
      lookupTiming: parseLookupTiming(lookupTimingHeader),
      lookupTimingHeaderBytes: byteSize(lookupTimingHeader),
      json,
    }
  } catch (err) {
    return {
      ok: false,
      status: null,
      elapsedMs: Math.round(performance.now() - started),
      bytes: 0,
      error: err instanceof Error ? err.message : String(err),
      json: null,
    }
  } finally {
    clearTimeout(timeout)
  }
}

function payloadSizes(json) {
  const payload = json?.report_payload ?? null
  const profile = payload?.report_profile ?? null
  return {
    total: jsonSize(json),
    evidence: jsonSize(json?.evidence),
    report_payload: jsonSize(payload),
    report_profile: jsonSize(profile),
    gene_context_snapshot: jsonSize(profile?.gene_context_snapshot),
    molecular_context: jsonSize(profile?.molecular_context),
    population_frequency: jsonSize(profile?.population_frequency),
    publications_literature: jsonSize(payload?.publications_literature),
    therapies_trials: jsonSize(profile?.therapies_trials),
    curated_variants_distribution: jsonSize(payload?.curated_variants_distribution),
    call_cards: jsonSize(payload?.call_cards),
  }
}

function reportFacts(json) {
  const payload = json?.report_payload ?? {}
  const profile = payload.report_profile ?? {}
  return {
    warnings: Array.isArray(json?.warnings) ? json.warnings.slice(0, 8) : [],
    publicationsInline: payload.publications_literature != null,
    trialsInline: profile.therapies_trials != null,
    geneContextStatus: profile.gene_context_snapshot?.source_status ?? null,
    populationStatus: profile.population_frequency?.source_status ?? null,
  }
}

function jsonSize(value) {
  if (value == null) return 0
  return byteSize(JSON.stringify(value))
}

function byteSize(value) {
  return Buffer.byteLength(String(value ?? ''), 'utf8')
}

function errorSummary(json, text) {
  if (json?.detail) return typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail)
  return text ? text.slice(0, 500) : 'request failed'
}

function parseLookupTiming(value) {
  if (!value) return null
  try {
    return JSON.parse(value)
  } catch {
    return { parse_error: 'invalid_lookup_timing_header', raw_bytes: byteSize(value) }
  }
}

function summarizeVariantRuns(runs) {
  const stats = {
    lookup: resultStats(runs.map((run) => run.lookup)),
    summary: resultStats(runs.map((run) => run.summary)),
    sections: {},
    viewer: skipViewer ? null : resultStats(runs.map((run) => run.viewer).filter(Boolean)),
    lookupPayloadBytes: payloadStats(runs.map((run) => run.lookup?.payloadSizes)),
  }
  if (!skipSections) {
    for (const section of sections) {
      stats.sections[section] = resultStats(runs.map((run) => run.sections[section]))
      stats.sections[section].payloadBytes = payloadStats(
        runs.map((run) => run.sections[section]?.payloadSizes),
      )
    }
  }
  return stats
}

function resultStats(results) {
  const present = results.filter(Boolean)
  return {
    runs: present.length,
    ok: present.filter((result) => result.ok).length,
    statuses: countBy(present.map((result) => result.status ?? 'ERR')),
    elapsedMs: numberStats(present.map((result) => result.elapsedMs)),
    bytes: numberStats(present.map((result) => result.bytes)),
    coldMs: present[0]?.elapsedMs ?? null,
    warmMs: numberStats(present.slice(1).map((result) => result.elapsedMs)),
  }
}

function payloadStats(values) {
  const present = values.filter(Boolean)
  if (present.length === 0) return null
  return {
    total: numberStats(present.map((item) => item.total)),
    reportPayload: numberStats(present.map((item) => item.report_payload)),
    sectionEnvelope: numberStats(present.map((item) => item.sectionEnvelope)),
    sectionPayload: numberStats(present.map((item) => item.sectionPayload)),
  }
}

function numberStats(values) {
  const numbers = values.filter((value) => Number.isFinite(value)).sort((a, b) => a - b)
  if (numbers.length === 0) {
    return { n: 0, min: null, p50: null, p95: null, max: null, avg: null }
  }
  const sum = numbers.reduce((total, value) => total + value, 0)
  return {
    n: numbers.length,
    min: numbers[0],
    p50: percentile(numbers, 50),
    p95: percentile(numbers, 95),
    max: numbers[numbers.length - 1],
    avg: Math.round(sum / numbers.length),
  }
}

function percentile(sortedNumbers, percentileValue) {
  if (sortedNumbers.length === 0) return null
  const index = Math.max(
    0,
    Math.min(sortedNumbers.length - 1, Math.ceil((percentileValue / 100) * sortedNumbers.length) - 1),
  )
  return sortedNumbers[index]
}

function countBy(values) {
  const counts = {}
  for (const value of values) {
    const key = String(value)
    counts[key] = (counts[key] ?? 0) + 1
  }
  return counts
}

function thresholdViolations(entry, limits) {
  const violations = []
  for (const run of entry.runs) {
    if (limits.lookupResponseBytes != null && run.lookup.bytes > limits.lookupResponseBytes) {
      violations.push({
        variant: entry.variant,
        run: run.run,
        target: 'lookup_response_bytes',
        observed: run.lookup.bytes,
        limit: limits.lookupResponseBytes,
      })
    }
    const lookupSizes = run.lookup.payloadSizes
    if (
      limits.reportPayloadBytes != null &&
      lookupSizes?.report_payload > limits.reportPayloadBytes
    ) {
      violations.push({
        variant: entry.variant,
        run: run.run,
        target: 'report_payload_bytes',
        observed: lookupSizes.report_payload,
        limit: limits.reportPayloadBytes,
      })
    }
    if (!skipSections) {
      for (const [section, result] of Object.entries(run.sections)) {
        if (
          limits.sectionEnvelopeBytes != null &&
          result.payloadSizes?.sectionEnvelope > limits.sectionEnvelopeBytes
        ) {
          violations.push({
            variant: entry.variant,
            run: run.run,
            section,
            target: 'section_envelope_bytes',
            observed: result.payloadSizes.sectionEnvelope,
            limit: limits.sectionEnvelopeBytes,
          })
        }
        if (
          limits.sectionPayloadBytes != null &&
          result.payloadSizes?.sectionPayload > limits.sectionPayloadBytes
        ) {
          violations.push({
            variant: entry.variant,
            run: run.run,
            section,
            target: 'section_payload_bytes',
            observed: result.payloadSizes.sectionPayload,
            limit: limits.sectionPayloadBytes,
          })
        }
      }
    }
  }
  return violations
}

function requiredEndpointFailures(entry) {
  const failures = []
  const inspect = (run, target, result) => {
    if (result?.ok) return
    failures.push({
      variant: entry.variant,
      run: run.run,
      target,
      status: result?.status ?? null,
      error: result?.error ?? 'request failed',
    })
  }

  for (const run of entry.runs) {
    inspect(run, 'lookup', run.lookup)
    inspect(run, 'summary', run.summary)
    for (const [section, result] of Object.entries(run.sections)) {
      inspect(run, `section:${section}`, result)
    }
    if (!skipViewer) inspect(run, 'viewer', run.viewer)
  }
  return failures
}

function printHuman(data) {
  console.log(`eamos-report-performance-audit | ${data.baseUrl}`)
  console.log(`generated_at=${data.generatedAt}`)
  console.log(`runs=${data.runCount} timeout_ms=${data.timeoutMs}`)
  if (data.requireOk) console.log('require_ok=true')
  if (Object.keys(data.thresholds).length > 0) {
    console.log(`thresholds=${JSON.stringify(data.thresholds)}`)
  }
  console.log('')
  for (const item of data.variants) {
    console.log(item.variant)
    for (const run of item.runs) {
      if (item.runs.length > 1) console.log(`  run ${run.run} (${run.phase})`)
      const prefix = item.runs.length > 1 ? '    ' : '  '
      printResult(`${prefix}lookup`, run.lookup)
      if (run.lookup.payloadSizes) {
        const sizes = run.lookup.payloadSizes
        console.log(
          `${prefix}payload bytes: total=${sizes.total} evidence=${sizes.evidence} report_profile=${sizes.report_profile} gene_context=${sizes.gene_context_snapshot} molecular=${sizes.molecular_context}`,
        )
        const facts = run.lookup.reportFacts
        console.log(
          `${prefix}inline: publications=${facts.publicationsInline ? 'yes' : 'no'} trials=${facts.trialsInline ? 'yes' : 'no'} gene_context_status=${facts.geneContextStatus ?? 'n/a'} population_status=${facts.populationStatus ?? 'n/a'}`,
        )
        if (facts.warnings.length > 0) {
          console.log(`${prefix}warnings: ${facts.warnings.join(', ')}`)
        }
      }
      printResult(`${prefix}summary`, run.summary)
      for (const [section, result] of Object.entries(run.sections)) {
        const status = result.sectionStatus ? ` section_status=${result.sectionStatus}` : ''
        const sectionBytes = result.payloadSizes
          ? ` envelope_bytes=${result.payloadSizes.sectionEnvelope} payload_bytes=${result.payloadSizes.sectionPayload}`
          : ''
        printResult(`${prefix}section:${section}`, result, `${status}${sectionBytes}`)
      }
      if (run.viewer) printResult(`${prefix}viewer`, run.viewer)
    }
    printStats(item.stats)
    console.log('')
  }
  if (data.violations.length > 0) {
    console.log('threshold violations:')
    for (const violation of data.violations) {
      const section = violation.section ? ` section=${violation.section}` : ''
      console.log(
        `  ${violation.variant} run=${violation.run}${section} ${violation.target}=${violation.observed} > ${violation.limit}`,
      )
    }
  }
  if (data.requiredEndpointFailures.length > 0) {
    console.log('required endpoint failures:')
    for (const failure of data.requiredEndpointFailures) {
      console.log(
        `  ${failure.variant} run=${failure.run} ${failure.target} status=${failure.status ?? 'ERR'} error=${failure.error}`,
      )
    }
  }
}

function printResult(label, result, suffix = '') {
  const status = result.status == null ? 'ERR' : result.status
  const err = result.error ? ` error=${result.error}` : ''
  console.log(`  ${label}: status=${status} ms=${result.elapsedMs} bytes=${result.bytes}${suffix}${err}`)
  if (result.lookupTiming) {
    printLookupTiming(result.lookupTiming, result.lookupTimingHeaderBytes)
  }
}

function printStats(stats) {
  if (!stats) return
  console.log(
    `  aggregate lookup: ${formatStats(stats.lookup.elapsedMs)} cold_ms=${stats.lookup.coldMs ?? 'n/a'} warm=${formatStats(stats.lookup.warmMs)}`,
  )
  console.log(
    `  aggregate summary: ${formatStats(stats.summary.elapsedMs)} cold_ms=${stats.summary.coldMs ?? 'n/a'} warm=${formatStats(stats.summary.warmMs)}`,
  )
  if (stats.lookupPayloadBytes) {
    console.log(
      `  aggregate payload bytes: total=${formatStats(stats.lookupPayloadBytes.total, 'B')} report_payload=${formatStats(stats.lookupPayloadBytes.reportPayload, 'B')}`,
    )
  }
  for (const [section, sectionStats] of Object.entries(stats.sections ?? {})) {
    console.log(`  aggregate section:${section}: ${formatStats(sectionStats.elapsedMs)}`)
    if (sectionStats.payloadBytes) {
      console.log(
        `    section payload bytes: envelope=${formatStats(sectionStats.payloadBytes.sectionEnvelope, 'B')} payload=${formatStats(sectionStats.payloadBytes.sectionPayload, 'B')}`,
      )
    }
  }
  if (stats.viewer) {
    console.log(`  aggregate viewer: ${formatStats(stats.viewer.elapsedMs)}`)
  }
}

function formatStats(stats, unit = 'ms') {
  if (!stats || stats.n === 0) return 'n=0'
  return `n=${stats.n} p50=${stats.p50}${unit} p95=${stats.p95}${unit} min=${stats.min}${unit} max=${stats.max}${unit} avg=${stats.avg}${unit}`
}

function printLookupTiming(timing, headerBytes) {
  if (timing.parse_error) {
    console.log(`    timing: ${timing.parse_error} bytes=${headerBytes}`)
    return
  }
  const phaseText = topTimingRows(timing.phases, 4)
  const providerText = topTimingRows(timing.providers, 5)
  const truncated = timing.truncated ? ' truncated=yes' : ''
  console.log(`    timing: total_ms=${timing.total_ms ?? 'n/a'} header_bytes=${headerBytes}${truncated}`)
  if (phaseText) console.log(`    slow phases: ${phaseText}`)
  if (providerText) console.log(`    slow providers: ${providerText}`)
}

function topTimingRows(rows, limit) {
  if (!Array.isArray(rows) || rows.length === 0) return ''
  return rows
    .slice()
    .sort((a, b) => Number(b.ms ?? 0) - Number(a.ms ?? 0))
    .slice(0, limit)
    .map((row) => `${row.name ?? 'unknown'}=${row.ms ?? 'n/a'}ms`)
    .join(', ')
}
