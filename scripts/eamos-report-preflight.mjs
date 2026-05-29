#!/usr/bin/env node
// eamos-report-preflight — proprietary mobile-overflow + contract-coverage scan.
//
// Drives a headless Chromium via the Chrome DevTools Protocol (dep-free; uses
// Node 24's native WebSocket + fetch + child_process.spawn) to detect:
//   • horizontal-overflow offenders at one or more viewport widths
//   • LazySection coverage (which sections are present in the eager DOM vs
//     wrapped in <LazySection>, so DL-013 lazy-eligibility drift is visible)
//   • console errors emitted during the report render
//
// The scan runs against any URL that returns the /report React tree — by
// default http://localhost:3000/report?demo (Next.js dev server).
//
// Usage:
//   node scripts/eamos-report-preflight.mjs                       # defaults
//   node scripts/eamos-report-preflight.mjs --url=URL --widths=375,768
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
//
// Exit codes: 0 if no fixable offenders + no console errors + all forced lazy
// sections resolved to `ready`. Non-zero otherwise.

import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// ─────────────────────────────────────────────────────────────────────────────
// CLI args

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v = 'true'] = a.replace(/^--/, '').split('=')
    return [k, v]
  }),
)
const URL_BASE = args.url ?? 'http://localhost:3000/report?demo'
const WIDTHS = String(args.widths ?? '375,768')
  .split(',')
  .map((n) => Number.parseInt(n, 10))
  .filter((n) => Number.isFinite(n) && n > 0)
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
  const lazyEligible = ['publications', 'computational_deep_dive', 'clingen_vcep'];
  const lazyPresent = Array.from(document.querySelectorAll('[data-lazy-section]'))
    .map((n) => n.getAttribute('data-lazy-section'));
  return {
    viewport: { vw: window.innerWidth, vh: window.innerHeight, dpr: window.devicePixelRatio },
    htmlOverflow: html.scrollWidth - html.clientWidth,
    bodyOverflow: body.scrollWidth - body.clientWidth,
    offenders,
    lazy: {
      eligible: lazyEligible,
      wrapped: lazyPresent,
      missing: lazyEligible.filter((id) => !lazyPresent.includes(id)),
    },
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
      }
    } else if (evt.method === 'Network.responseReceived') {
      const id = evt.params?.requestId
      const found = sectionFetches.find((f) => f.requestId === id)
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
    mobile: width <= 480,
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
  return { width, navUrl, scan: result, consoleErrors, sectionFetches, lazyResults }
}

// ─────────────────────────────────────────────────────────────────────────────
// Output

function isFixable(o) {
  if (IGNORE_LOCUS_MARKER && o.cls?.includes('locus-marker')) return false
  return true
}

function formatHuman(report) {
  const lines = []
  lines.push(`eamos-report-preflight · ${report.urlBase}`)
  if (report.lazyForced.length) {
    lines.push(`  lazy-forced sections: ${report.lazyForced.join(', ')}`)
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
    if (r.consoleErrors.length) {
      lines.push(`  console errors:`)
      for (const e of r.consoleErrors) lines.push(`    ${e.kind}: ${e.text}`)
    }
  }
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
let exit = 0
try {
  for (const w of WIDTHS) {
    const r = await runAtWidth(host, port, w)
    results.push(r)
    const fixable = (r.scan?.offenders ?? []).filter(isFixable)
    if (fixable.length > 0) exit = 1
    if (r.consoleErrors.length > 0) exit = 1
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
  widths: WIDTHS,
  results,
}

if (JSON_OUT) {
  process.stdout.write(JSON.stringify(report, null, 2) + '\n')
} else {
  process.stdout.write(formatHuman(report) + '\n')
}

process.exit(exit)
