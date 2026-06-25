#!/usr/bin/env node
// eamos-report-performance-audit - read-only latency/payload audit for /report data paths.
//
// Examples:
//   node scripts/eamos-report-performance-audit.mjs
//   node scripts/eamos-report-performance-audit.mjs --base=https://eamos-dev-sg.onrender.com
//   node scripts/eamos-report-performance-audit.mjs --variant="ABCA4:c.5435T>A" --json

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
const timeoutMs = Number(args.timeout ?? 180000)
const emitJson = Boolean(args.json)
const skipSections = Boolean(args['skip-sections'])
const skipViewer = Boolean(args['skip-viewer'])

const report = {
  tool: 'eamos-report-performance-audit',
  baseUrl,
  timeoutMs,
  generatedAt: new Date().toISOString(),
  variants: [],
}

for (const variantText of variants) {
  const variant = parseVariant(variantText)
  const body = { gene: variant.gene, cdna: variant.cdna, species: 'human' }
  const entry = {
    variant: `${variant.gene}:${variant.cdna}`,
    lookup: await timedPost('/api/v1/lookup', body),
    summary: await timedPost('/api/v1/lookup/summary', body),
    sections: {},
    viewer: null,
  }

  if (entry.lookup.ok && entry.lookup.json) {
    entry.lookup.payloadSizes = payloadSizes(entry.lookup.json)
    entry.lookup.reportFacts = reportFacts(entry.lookup.json)
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
      entry.sections[section] = result
    }
  }
  if (!skipViewer) {
    entry.viewer = await timedPost('/api/v1/viewer', {
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
  report.variants.push(entry)
}

if (emitJson) {
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
} else {
  printHuman(report)
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

function printHuman(data) {
  console.log(`eamos-report-performance-audit | ${data.baseUrl}`)
  console.log(`generated_at=${data.generatedAt}`)
  console.log('')
  for (const item of data.variants) {
    console.log(item.variant)
    printResult('lookup', item.lookup)
    if (item.lookup.payloadSizes) {
      const sizes = item.lookup.payloadSizes
      console.log(
        `  payload bytes: total=${sizes.total} evidence=${sizes.evidence} report_profile=${sizes.report_profile} gene_context=${sizes.gene_context_snapshot} molecular=${sizes.molecular_context}`,
      )
      const facts = item.lookup.reportFacts
      console.log(
        `  inline: publications=${facts.publicationsInline ? 'yes' : 'no'} trials=${facts.trialsInline ? 'yes' : 'no'} gene_context_status=${facts.geneContextStatus ?? 'n/a'} population_status=${facts.populationStatus ?? 'n/a'}`,
      )
      if (facts.warnings.length > 0) {
        console.log(`  warnings: ${facts.warnings.join(', ')}`)
      }
    }
    printResult('summary', item.summary)
    for (const [section, result] of Object.entries(item.sections)) {
      const status = result.sectionStatus ? ` section_status=${result.sectionStatus}` : ''
      const sectionBytes = result.payloadSizes
        ? ` envelope_bytes=${result.payloadSizes.sectionEnvelope} payload_bytes=${result.payloadSizes.sectionPayload}`
        : ''
      printResult(`section:${section}`, result, `${status}${sectionBytes}`)
    }
    if (item.viewer) printResult('viewer', item.viewer)
    console.log('')
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
