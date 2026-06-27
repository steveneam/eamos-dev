#!/usr/bin/env node
// eamos-report-preflight — proprietary desktop overflow + contract-coverage scan.
//
// Drives a headless Chromium via the Chrome DevTools Protocol (dep-free; uses
// Node 24's native WebSocket + fetch + child_process.spawn) to detect:
//   • horizontal-overflow offenders at desktop widths
//   • LazySection coverage (which sections are present in the eager DOM vs
//     wrapped in <LazySection>, so DL-013 lazy-eligibility drift is visible)
//   • console errors emitted during the report render
//
// The scan runs against any URL that returns the /report React tree — by
// default http://localhost:3000/report?fixture=rpe65-negative (Next.js dev
// server). Sub-desktop/mobile overflow checks are disabled by Steven until he
// explicitly reactivates them.
//
// Usage:
//   node scripts/eamos-report-preflight.mjs                       # desktop fixture default
//   node scripts/eamos-report-preflight.mjs --url=URL --widths=1280,1440
//   node scripts/eamos-report-preflight.mjs --json                # machine output
//   node scripts/eamos-report-preflight.mjs --ignore-locus-marker # filter the
//                                                                  # known
//                                                                  # 1px-wide
//                                                                  # variant
//                                                                  # anchor
//   node scripts/eamos-report-preflight.mjs --lazy=publications   # M11/M-007
//     # contract canary: appends `&lazy=<csv>` so ReportClient forces the
//     # matching LazySection wrappers into their lazy branch, then auto-scrolls
//     # to drive IntersectionObserver and reports each section's terminal
//     # state (sentinel-stuck / ready / error). Works today against Codex's
//     # already-shipped /api/v1/lookup/sections endpoint.
//   node scripts/eamos-report-preflight.mjs --forbid-viewer
//     # fail if report first paint requests /api/v1/viewer. Use this when the
//     # lookup payload is expected to include gene_context_snapshot.
//   node scripts/eamos-report-preflight.mjs --validate-registry
//     # validate REPORT_SECTION_REGISTRY shape and exit without launching Chrome.
//
// Exit codes: 0 if no fixable offenders + no console errors + all forced lazy
// sections resolved to `ready`. Non-zero otherwise.

import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync, existsSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// ─────────────────────────────────────────────────────────────────────────────
// CLI args

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const raw = a.replace(/^--/, '')
    const sep = raw.indexOf('=')
    if (sep === -1) return [raw, 'true']
    return [raw.slice(0, sep), raw.slice(sep + 1)]
  }),
)
const URL_BASE = args.url ?? 'http://localhost:3000/report?fixture=rpe65-negative'
const DESKTOP_MIN_WIDTH = 1024
const RAW_WIDTHS = String(args.widths ?? '1280')
  .split(',')
  .map((n) => Number.parseInt(n, 10))
  .filter((n) => Number.isFinite(n) && n > 0)
const WIDTHS = RAW_WIDTHS.filter((n) => n >= DESKTOP_MIN_WIDTH)
if (WIDTHS.length === 0) WIDTHS.push(1280)
const SKIPPED_SUB_DESKTOP_WIDTHS = RAW_WIDTHS.filter((n) => n < DESKTOP_MIN_WIDTH)
const JSON_OUT = args.json === 'true'
const IGNORE_LOCUS_MARKER = args['ignore-locus-marker'] === 'true'
const REMOTE_PORT = args.port ? Number.parseInt(args.port, 10) : null
const TIMEOUT_MS = Number.parseInt(args.timeout ?? '15000', 10)
const LAZY_FORCE = String(args.lazy ?? '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
const LAZY_SETTLE_MS = Number.parseInt(args['lazy-settle'] ?? '30000', 10)
const LAZY_POLL_MS = Number.parseInt(args['lazy-poll'] ?? '500', 10)
const FORBID_VIEWER = args['forbid-viewer'] === 'true'
const VALIDATE_REGISTRY = args['validate-registry'] === 'true'

const REPORT_SECTION_REGISTRY = JSON.parse(
  readFileSync(new URL('../app/web/lib/report-section-registry.json', import.meta.url), 'utf8'),
).sections
const PREFLIGHT_REQUIRED_SECTION_SLOTS = REPORT_SECTION_REGISTRY
  .filter((section) => section.preflightRequired)
  .map((section) => ({
    id: section.id,
    anchorId: section.anchorId,
    label: section.label,
    title: section.title,
  }))
const LAZY_ELIGIBLE_SECTION_IDS = REPORT_SECTION_REGISTRY
  .map((section) => section.lazySectionId)
  .filter(Boolean)
const REGISTRY_VALIDATION = validateReportSectionRegistry(REPORT_SECTION_REGISTRY)

if (VALIDATE_REGISTRY) {
  const report = {
    tool: 'eamos-report-preflight',
    mode: 'validate-registry',
    registryValidation: REGISTRY_VALIDATION,
  }
  if (JSON_OUT) {
    process.stdout.write(JSON.stringify(report, null, 2) + '\n')
  } else {
    process.stdout.write(formatRegistryValidation(report) + '\n')
  }
  process.exit(REGISTRY_VALIDATION.ok ? 0 : 1)
}

function validateReportSectionRegistry(sections) {
  const errors = []
  const warnings = []
  const validLoadPolicies = new Set(['eager', 'lazy', 'eager_with_lazy_panel'])
  const validSkeletons = new Set(['card_skeleton', 'panel_skeleton'])
  const validLazyIds = new Set([
    'publications',
    'therapies_trials',
    'computational_deep_dive',
    'clingen_vcep',
  ])
  const requiredTextFields = [
    'id',
    'anchorId',
    'label',
    'title',
    'meta',
    'emptyState',
    'partialState',
    'failedState',
    'staleState',
    'eagerPayloadSelector',
  ]
  const ids = new Set()
  const anchors = new Set()
  const numbers = new Set()
  for (const [index, section] of sections.entries()) {
    const label = section?.id ?? `#${index}`
    for (const field of requiredTextFields) {
      if (typeof section?.[field] !== 'string' || section[field].trim() === '') {
        errors.push(`${label}: missing non-empty ${field}`)
      }
    }
    if (ids.has(section.id)) errors.push(`${label}: duplicate id`)
    ids.add(section.id)
    if (anchors.has(section.anchorId)) errors.push(`${label}: duplicate anchorId ${section.anchorId}`)
    anchors.add(section.anchorId)
    if (!Number.isInteger(section.number) || section.number < 1) {
      errors.push(`${label}: number must be a positive integer`)
    } else if (numbers.has(section.number)) {
      errors.push(`${label}: duplicate number ${section.number}`)
    }
    numbers.add(section.number)
    if (!validLoadPolicies.has(section.loadPolicy)) {
      errors.push(`${label}: unsupported loadPolicy ${section.loadPolicy}`)
    }
    if (!validSkeletons.has(section.skeleton)) {
      errors.push(`${label}: unsupported skeleton ${section.skeleton}`)
    }
    if (section.preflightRequired && !section.requiredSlot) {
      errors.push(`${label}: preflightRequired sections must also be requiredSlot`)
    }
    if (section.loadPolicy === 'lazy' || section.loadPolicy === 'eager_with_lazy_panel') {
      if (!validLazyIds.has(section.lazySectionId)) {
        errors.push(`${label}: lazy load policy needs a valid lazySectionId`)
      }
      if (typeof section.lazyFetchContract !== 'string' || section.lazyFetchContract.trim() === '') {
        errors.push(`${label}: lazy load policy needs lazyFetchContract`)
      }
    }
    if (Array.isArray(section.aliasAnchors)) {
      for (const alias of section.aliasAnchors) {
        if (anchors.has(alias)) errors.push(`${label}: duplicate alias anchor ${alias}`)
        anchors.add(alias)
      }
    }
    if (!Array.isArray(section.signalIds) || section.signalIds.length === 0) {
      warnings.push(`${label}: no signalIds registered`)
    }
  }
  const sortedNumbers = [...numbers].sort((a, b) => a - b)
  const expected = Array.from({ length: sections.length }, (_, i) => i + 1)
  if (sortedNumbers.join(',') !== expected.join(',')) {
    errors.push(`section numbers must be contiguous 1..${sections.length}`)
  }
  return {
    ok: errors.length === 0,
    sectionCount: sections.length,
    requiredSlotCount: sections.filter((section) => section.requiredSlot).length,
    preflightRequiredCount: sections.filter((section) => section.preflightRequired).length,
    lazySectionIds: LAZY_ELIGIBLE_SECTION_IDS,
    errors,
    warnings,
  }
}

function buildUrl(width) {
  if (LAZY_FORCE.length === 0) return URL_BASE
  const sep = URL_BASE.includes('?') ? '&' : '?'
  return `${URL_BASE}${sep}lazy=${encodeURIComponent(LAZY_FORCE.join(','))}`
}

// ─────────────────────────────────────────────────────────────────────────────
// Chrome discovery

function findChrome() {
  const candidates = [
    process.env.CHROME,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ].filter(Boolean)
  for (const c of candidates) {
    if (existsSync(c)) return c
  }
  throw new Error(
    'Could not locate Chrome / Edge. Set $env:CHROME to a chromium-flavored browser path.',
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// CDP — minimal client (HTTP + WebSocket)

class CDP {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl)
    this.id = 0
    this.pending = new Map()
    this.events = []
    this.eventListeners = new Set()
    this.ready = new Promise((resolve, reject) => {
      this.ws.addEventListener('open', () => resolve())
      this.ws.addEventListener('error', (e) => reject(e))
    })
    this.ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data)
      if (msg.id != null && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) reject(new Error(msg.error.message))
        else resolve(msg.result)
      } else if (msg.method) {
        this.events.push(msg)
        for (const l of this.eventListeners) l(msg)
      }
    })
  }
  on(fn) {
    this.eventListeners.add(fn)
    return () => this.eventListeners.delete(fn)
  }
  send(method, params = {}) {
    const id = ++this.id
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }
  close() {
    try {
      this.ws.close()
    } catch {}
  }
}

async function getJson(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`HTTP ${r.status} from ${url}`)
  return r.json()
}

async function newPageWS(host, port) {
  // POST /json/new?about:blank → returns a JSON descriptor for the new tab.
  // Older Chrome versions allowed GET; newer require PUT. Try PUT first.
  for (const method of ['PUT', 'GET']) {
    const r = await fetch(`http://${host}:${port}/json/new?about:blank`, { method })
    if (r.ok) return r.json()
  }
  throw new Error('Could not open a new tab via /json/new')
}

// ─────────────────────────────────────────────────────────────────────────────
// In-browser scan — injected via Runtime.evaluate, returns JSON-serializable.

const SCAN_FN = `
(() => {
  const html = document.documentElement;
  const body = document.body;
  const offenders = [];
  const seen = new Set();
  for (const el of document.querySelectorAll('*')) {
    if (!(el instanceof HTMLElement)) continue;
    if (el.closest('.sr-only')) continue;
    const sw = el.scrollWidth, cw = el.clientWidth;
    if (sw > cw + 1 && cw > 0) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const cs = getComputedStyle(el);
      if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') continue;
      let p = el.parentElement, skip = false;
      while (p) { if (seen.has(p)) { skip = true; break; } p = p.parentElement; }
      if (skip) continue;
      // Skip if computed visibility/opacity hides the element entirely
      // (e.g. StickyVariantRibbon idles invisible until scroll past 200px).
      if (cs.visibility === 'hidden' || cs.opacity === '0') continue;
      seen.add(el);
      offenders.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className && el.className.toString().slice(0, 100)) || '',
        sw, cw, delta: sw - cw,
        top: Math.round(rect.top),
        text: (el.innerText || '').slice(0, 60).replace(/\\s+/g, ' ').trim(),
        path: (() => {
          const parts = [];
          let cur = el;
          for (let i = 0; i < 4 && cur; i++) {
            const t = cur.tagName.toLowerCase();
            const c = (cur.className && cur.className.toString().split(/\\s+/).filter(Boolean).slice(0,2).join('.')) || '';
            parts.unshift(c ? t + '.' + c : t);
            cur = cur.parentElement;
          }
          return parts.join(' > ');
        })(),
      });
    }
  }
  // LazySection coverage — which DL-013 lazy-eligible sections are wrapped in
  // <LazySection> (data-lazy-section attr survives eager-mode too because the
  // wrapper always renders the sentinel during idle/loading).
  const lazyEligible = ${JSON.stringify(LAZY_ELIGIBLE_SECTION_IDS)};
  const lazyPresent = Array.from(document.querySelectorAll('[data-lazy-section]'))
    .map((n) => n.getAttribute('data-lazy-section'));
  const requiredSectionSlots = ${JSON.stringify(PREFLIGHT_REQUIRED_SECTION_SLOTS)};
  const sectionSlots = Array.from(document.querySelectorAll('[data-report-section-slot]'))
    .map((n) => ({
      id: n.getAttribute('data-report-section-slot'),
      required: n.getAttribute('data-report-section-required') === 'true',
      preflight: n.getAttribute('data-report-section-preflight') === 'true',
      text: (n.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
    }));
  const cardTitles = Array.from(document.querySelectorAll('h2'))
    .map((n) => (n.textContent || '').replace(/\\s+/g, ' ').trim())
    .filter(Boolean);
  const presentSlotIds = new Set(sectionSlots.map((slot) => slot.id).filter(Boolean));
  const missingSlots = requiredSectionSlots.filter((slot) => !presentSlotIds.has(slot.id));
  const missingAnchors = requiredSectionSlots.filter((slot) => !document.getElementById(slot.anchorId));
  return {
    viewport: { vw: window.innerWidth, vh: window.innerHeight, dpr: window.devicePixelRatio },
    htmlOverflow: html.scrollWidth - html.clientWidth,
    bodyOverflow: body.scrollWidth - body.clientWidth,
    offenders,
    report: {
      requiredSlots: requiredSectionSlots,
      sectionSlots,
      cardTitles,
      missingSlots,
      missingAnchors,
    },
    lazy: {
      eligible: lazyEligible,
      wrapped: lazyPresent,
      missing: lazyEligible.filter((id) => !lazyPresent.includes(id)),
    },
  };
})()
`

const REPORT_READY_FN = `
(() => {
  const requiredSectionSlots = ${JSON.stringify(PREFLIGHT_REQUIRED_SECTION_SLOTS)};
  const presentSlotIds = new Set(
    Array.from(document.querySelectorAll('[data-report-section-slot]'))
      .map((n) => n.getAttribute('data-report-section-slot'))
      .filter(Boolean)
  );
  const cardTitles = Array.from(document.querySelectorAll('h2'))
    .map((n) => (n.textContent || '').replace(/\\s+/g, ' ').trim())
    .filter(Boolean);
  const alerts = Array.from(document.querySelectorAll('[role="alert"]'))
    .map((n) => (n.textContent || '').replace(/\\s+/g, ' ').trim())
    .filter(Boolean);
  const missingSlots = requiredSectionSlots.filter((slot) => !presentSlotIds.has(slot.id));
  return {
    ready: missingSlots.length === 0 || alerts.some((text) => /could not load|failed|error/i.test(text)),
    missingSlots,
    cardTitles,
    alerts: alerts.slice(0, 4),
  };
})()
`

// ─────────────────────────────────────────────────────────────────────────────
// Main

async function spawnChrome() {
  const chromePath = findChrome()
  const userDataDir = mkdtempSync(join(tmpdir(), 'eamos-preflight-'))
  const proc = spawn(
    chromePath,
    [
      '--headless=new',
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      '--remote-debugging-port=0',
      '--remote-debugging-address=127.0.0.1',
      `--user-data-dir=${userDataDir}`,
      'about:blank',
    ],
    { stdio: ['ignore', 'pipe', 'pipe'] },
  )
  const port = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Chrome boot timeout')), TIMEOUT_MS)
    const onData = (buf) => {
      const m = String(buf).match(/DevTools listening on ws:\/\/[^:]+:(\d+)\//)
      if (m) {
        clearTimeout(timer)
        proc.stderr.off('data', onData)
        resolve(Number.parseInt(m[1], 10))
      }
    }
    proc.stderr.on('data', onData)
    proc.on('exit', (code) => reject(new Error(`Chrome exited early: ${code}`)))
  })
  const cleanup = () => {
    try {
      proc.kill()
    } catch {}
    try {
      rmSync(userDataDir, { recursive: true, force: true })
    } catch {}
  }
  return { port, cleanup }
}

// In-browser scroll driver: first explicitly bring every `[data-lazy-section]`
// into view so IntersectionObserver fires deterministically in headless,
// THEN walk down the page so any non-lazy below-the-fold sections paint.
// scrollIntoView is the reliable trigger in --headless=new; paginated scroll
// alone can race the observer's first cycle on a cold page.
const SCROLL_FN = `
async () => {
  const log = { sentinels: 0, scrolledTo: 0, contentHeight: 0 };
  const sentinels = Array.from(document.querySelectorAll('[data-lazy-section]'));
  log.sentinels = sentinels.length;
  for (const s of sentinels) {
    s.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise((r) => setTimeout(r, 250));
  }
  const step = Math.max(200, Math.floor(window.innerHeight * 0.75));
  const max = document.documentElement.scrollHeight;
  log.contentHeight = max;
  let y = window.scrollY;
  while (y < max) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 120));
    y += step;
  }
  window.scrollTo(0, max);
  await new Promise((r) => setTimeout(r, 200));
  log.scrolledTo = y;
  return log;
}
`

// LazySection terminal-state probe — for each forced section ID, report
// whether the wrapper is still showing a sentinel (idle/loading), has rendered
// its DefaultErrorView (error), or has resolved into children (ready).
function buildLazyProbeFn(sectionIds) {
  return `
  (() => {
    const ids = ${JSON.stringify(sectionIds)};
    const out = {};
    for (const id of ids) {
      const sentinel = document.querySelector('[data-lazy-section="' + id + '"]');
      if (sentinel) {
        out[id] = {
          state: sentinel.getAttribute('aria-busy') === 'true' ? 'loading' : 'idle',
          text: (sentinel.textContent || '').slice(0, 100).trim(),
        };
        continue;
      }
      // Sentinel gone: either resolved into children or rendered DefaultErrorView.
      const alerts = Array.from(document.querySelectorAll('[role="alert"]'))
        .filter((el) => /Could not load section/i.test(el.textContent || ''));
      if (alerts.length) {
        out[id] = { state: 'error', text: (alerts[0].textContent || '').slice(0, 200).trim() };
        continue;
      }
      out[id] = { state: 'ready' };
    }
    return out;
  })()
  `
}

async function runAtWidth(host, port, width) {
  const tab = await newPageWS(host, port)
  const cdp = new CDP(tab.webSocketDebuggerUrl)
  await cdp.ready
  const consoleErrors = []
  const sectionFetches = []
  const viewerFetches = []
  cdp.on((evt) => {
    if (evt.method === 'Runtime.exceptionThrown') {
      consoleErrors.push({
        kind: 'exception',
        text: evt.params?.exceptionDetails?.exception?.description ?? 'unknown',
      })
    } else if (evt.method === 'Runtime.consoleAPICalled' && evt.params?.type === 'error') {
      const args = (evt.params.args ?? []).map((a) => a.value ?? a.description ?? '')
      consoleErrors.push({ kind: 'console.error', text: args.join(' ') })
    } else if (evt.method === 'Network.requestWillBeSent') {
      const url = evt.params?.request?.url ?? ''
      if (url.includes('/api/v1/lookup/sections')) {
        sectionFetches.push({ url, requestId: evt.params.requestId, status: null })
      } else if (url.includes('/api/v1/viewer')) {
        viewerFetches.push({ url, requestId: evt.params.requestId, status: null })
      }
    } else if (evt.method === 'Network.responseReceived') {
      const id = evt.params?.requestId
      const found = sectionFetches.find((f) => f.requestId === id)
        ?? viewerFetches.find((f) => f.requestId === id)
      if (found) found.status = evt.params?.response?.status ?? null
    }
  })
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Network.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height: 900,
    deviceScaleFactor: 2,
    mobile: false,
  })
  const navUrl = buildUrl(width)
  await cdp.send('Page.navigate', { url: navUrl })
  // Wait for load + a settle frame
  await new Promise((resolve) => {
    const stop = cdp.on((evt) => {
      if (evt.method === 'Page.loadEventFired') {
        stop()
        setTimeout(resolve, 600)
      }
    })
    setTimeout(() => {
      stop()
      resolve()
    }, TIMEOUT_MS)
  })
  let reportWait = null
  {
    const deadline = Date.now() + TIMEOUT_MS
    while (Date.now() < deadline) {
      const probeRes = await cdp.send('Runtime.evaluate', {
        expression: REPORT_READY_FN,
        returnByValue: true,
      })
      reportWait = probeRes?.result?.value ?? null
      if (reportWait?.ready) break
      await new Promise((r) => setTimeout(r, 500))
    }
  }

  // Lazy mode: drive the scroll so IntersectionObserver fires, then poll the
  // terminal-state probe until every forced section has resolved or we've
  // burned the settle budget. Polling beats a fixed sleep because backend
  // latency is workload-dependent (cold cache, real-API mode, or Codex
  // mid-edit can stretch /lookup/sections well past a static budget).
  let lazyResults = null
  if (LAZY_FORCE.length > 0) {
    await cdp.send('Runtime.evaluate', {
      expression: SCROLL_FN + '()',
      awaitPromise: true,
      returnByValue: true,
    })
    const deadline = Date.now() + LAZY_SETTLE_MS
    const probeExpr = buildLazyProbeFn(LAZY_FORCE)
    while (Date.now() < deadline) {
      const probeRes = await cdp.send('Runtime.evaluate', {
        expression: probeExpr,
        returnByValue: true,
      })
      lazyResults = probeRes?.result?.value ?? null
      const terminal = lazyResults
        && Object.values(lazyResults).every((info) => info.state === 'ready' || info.state === 'error')
      if (terminal) break
      await new Promise((r) => setTimeout(r, LAZY_POLL_MS))
    }
  }

  const evalRes = await cdp.send('Runtime.evaluate', {
    expression: SCAN_FN,
    returnByValue: true,
    awaitPromise: false,
  })
  cdp.close()
  try {
    await fetch(`http://${host}:${port}/json/close/${tab.id}`)
  } catch {}
  const result = evalRes?.result?.value ?? null
  return {
    width,
    navUrl,
    scan: result,
    consoleErrors,
    sectionFetches,
    viewerFetches,
    lazyResults,
    reportWait,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Output

function isFixable(o) {
  if (IGNORE_LOCUS_MARKER && o.cls?.includes('locus-marker')) return false
  return true
}

function formatHuman(report) {
  const lines = []
  const forbidViewer = Boolean(report.forbidViewer)
  lines.push(`eamos-report-preflight · ${report.urlBase}`)
  if (report.registryValidation) {
    lines.push(
      `  registry: ${report.registryValidation.ok ? 'ok' : 'failed'} · sections=${report.registryValidation.sectionCount} · required=${report.registryValidation.preflightRequiredCount}`,
    )
    for (const error of report.registryValidation.errors) lines.push(`    registry error: ${error}`)
    for (const warning of report.registryValidation.warnings) lines.push(`    registry warning: ${warning}`)
  }
  if (forbidViewer) {
    lines.push('  viewer requests forbidden: true')
  }
  if (report.lazyForced.length) {
    lines.push(`  lazy-forced sections: ${report.lazyForced.join(', ')}`)
  }
  if (report.skippedSubDesktopWidths.length) {
    lines.push(
      `  sub-desktop widths ignored: ${report.skippedSubDesktopWidths.join(', ')} (mobile overflow gate disabled)`,
    )
  }
  for (const r of report.results) {
    const fixable = r.scan?.offenders?.filter(isFixable) ?? []
    lines.push('')
    lines.push(`▸ ${r.width}px viewport  (${r.navUrl})`)
    lines.push(`  html overflow: ${r.scan?.htmlOverflow ?? '?'}px`)
    lines.push(`  body overflow: ${r.scan?.bodyOverflow ?? '?'}px`)
    lines.push(`  fixable offenders: ${fixable.length}`)
    for (const o of fixable) {
      lines.push(
        `    [+${o.delta}px @ top=${o.top}] ${o.path}` +
          (o.text ? `  «${o.text}»` : ''),
      )
    }
    if (r.scan?.lazy) {
      const { wrapped, eligible } = r.scan.lazy
      // `wrapped` = LazySection sentinels currently in the DOM. In eager-demo
      // mode the wrapper short-circuits on `eagerData`, so an empty list here
      // is informational, not a defect. After M-007 trims the eager payload,
      // eligible sections that scroll off-screen will reappear in `wrapped`.
      const mode = wrapped.length === 0 ? 'all-eager' : 'mixed'
      lines.push(
        `  LazySection: mode=${mode} · lazy-sentinels=[${wrapped.join(', ')}] · eligible=[${eligible.join(', ')}]`,
      )
    }
    if (r.scan?.report) {
      const missingSlots = (r.scan.report.missingSlots ?? []).map((slot) => slot.id)
      const missingAnchors = (r.scan.report.missingAnchors ?? []).map((slot) => slot.anchorId)
      lines.push(
        `  required report slots: missing=[${missingSlots.join(', ')}] / missing-anchors=[${missingAnchors.join(', ')}]`,
      )
    }
    if (r.lazyResults) {
      lines.push(`  lazy-resolution:`)
      for (const [id, info] of Object.entries(r.lazyResults)) {
        lines.push(`    ${id}: ${info.state}` + (info.text ? `  «${info.text.slice(0, 80)}»` : ''))
      }
    }
    if (r.sectionFetches?.length) {
      lines.push(`  /api/v1/lookup/sections fetches: ${r.sectionFetches.length}`)
      for (const f of r.sectionFetches) {
        lines.push(`    ${f.status ?? 'pending'}  ${f.url.split('?')[0]}`)
      }
    }
    if (r.viewerFetches?.length) {
      lines.push(`  /api/v1/viewer fetches: ${r.viewerFetches.length}`)
      for (const f of r.viewerFetches) {
        lines.push(`    ${f.status ?? 'pending'}  ${f.url.split('?')[0]}`)
      }
    }
    if (r.consoleErrors.length) {
      lines.push(`  console errors:`)
      for (const e of r.consoleErrors) lines.push(`    ${e.kind}: ${e.text}`)
    }
  }
  return lines.join('\n')
}

function formatRegistryValidation(report) {
  const validation = report.registryValidation
  const lines = []
  lines.push('eamos-report-preflight · registry validation')
  lines.push(`  status: ${validation.ok ? 'ok' : 'failed'}`)
  lines.push(`  sections: ${validation.sectionCount}`)
  lines.push(`  required slots: ${validation.requiredSlotCount}`)
  lines.push(`  preflight-required slots: ${validation.preflightRequiredCount}`)
  lines.push(`  lazy sections: [${validation.lazySectionIds.join(', ')}]`)
  for (const error of validation.errors) lines.push(`  error: ${error}`)
  for (const warning of validation.warnings) lines.push(`  warning: ${warning}`)
  return lines.join('\n')
}

// ─────────────────────────────────────────────────────────────────────────────
// Entrypoint

const host = '127.0.0.1'
let port = REMOTE_PORT
let cleanup = () => {}
if (port == null) {
  ;({ port, cleanup } = await spawnChrome())
}

try {
  await getJson(`http://${host}:${port}/json/version`)
} catch (err) {
  cleanup()
  console.error(`Could not reach Chrome CDP at http://${host}:${port}/json/version`)
  console.error(String(err))
  process.exit(2)
}

const results = []
let exit = REGISTRY_VALIDATION.ok ? 0 : 1
try {
  for (const w of WIDTHS) {
    const r = await runAtWidth(host, port, w)
    results.push(r)
    const fixable = (r.scan?.offenders ?? []).filter(isFixable)
    if (fixable.length > 0) exit = 1
    if (r.consoleErrors.length > 0) exit = 1
    if ((r.scan?.report?.missingSlots ?? []).length > 0) exit = 1
    if ((r.scan?.report?.missingAnchors ?? []).length > 0) exit = 1
    if (FORBID_VIEWER && r.viewerFetches.length > 0) exit = 1
    // Lazy mode: any forced section that did not resolve to 'ready' is a fail.
    if (r.lazyResults) {
      for (const info of Object.values(r.lazyResults)) {
        if (info.state !== 'ready') exit = 1
      }
    }
  }
} finally {
  cleanup()
}

const report = {
  tool: 'eamos-report-preflight',
  urlBase: URL_BASE,
  lazyForced: LAZY_FORCE,
  forbidViewer: FORBID_VIEWER,
  registryValidation: REGISTRY_VALIDATION,
  widths: WIDTHS,
  skippedSubDesktopWidths: SKIPPED_SUB_DESKTOP_WIDTHS,
  results,
}

if (JSON_OUT) {
  process.stdout.write(JSON.stringify(report, null, 2) + '\n')
} else {
  process.stdout.write(formatHuman(report) + '\n')
}

process.exit(exit)
