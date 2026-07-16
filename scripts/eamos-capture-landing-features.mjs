#!/usr/bin/env node

// Reproducible browser captures for the landing-page feature section.
// Run a local Eamos web server first, then:
//   node scripts/eamos-capture-landing-features.mjs --base-url=http://127.0.0.1:3001
//   node scripts/eamos-capture-landing-features.mjs --check

import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUTPUT_DIR = join(ROOT, 'app', 'web', 'public', 'features')
const MANIFEST_PATH = join(OUTPUT_DIR, 'capture-manifest.json')
const SAMPLE_VCF_PATH = join(ROOT, 'app', 'web', 'lib', 'sample-vcf.ts')
const WIDTH = 1440
const HEIGHT = 960
const QUALITY = 72
const MAX_ASSET_BYTES = 256 * 1024
const TIMEOUT_MS = 30_000

const args = Object.fromEntries(
  process.argv.slice(2).map((arg) => {
    const raw = arg.replace(/^--/, '')
    const separator = raw.indexOf('=')
    return separator === -1
      ? [raw, 'true']
      : [raw.slice(0, separator), raw.slice(separator + 1)]
  }),
)

const BASE_URL = String(args['base-url'] ?? 'http://localhost:3000').replace(/\/$/, '')

const CAPTURES = [
  {
    id: 'report',
    file: 'report-demo.webp',
    route: '/report?fixture=rpe65-negative',
    ready: `document.querySelectorAll('[data-report-section-slot]').length >= 3`,
    scrollTarget: '[data-report-section-slot="population_frequency"]',
  },
  {
    id: 'workbench',
    file: 'workbench-demo.webp',
    route: '/workbench?gene=RPE65&cdna=c.260A%3EG&transcript=NM_000329.3',
    ready: `document.body.innerText.includes('RPE65') && document.body.innerText.includes('Sequence')`,
  },
  {
    id: 'compare',
    file: 'compare-demo.webp',
    route: '/compare',
    ready: `document.body.innerText.includes('sample.vcf') && document.body.innerText.includes('Generate results')`,
  },
]

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex')
}

function webpDimensions(buffer) {
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WEBP') {
    throw new Error('not a WebP RIFF payload')
  }
  if (buffer.toString('ascii', 12, 16) !== 'VP8X' || buffer.length < 30) {
    throw new Error('expected Chrome VP8X capture payload')
  }
  return {
    width: buffer.readUIntLE(24, 3) + 1,
    height: buffer.readUIntLE(27, 3) + 1,
  }
}

function gitRevision() {
  const result = spawnSync('git', ['rev-parse', '--short=12', 'HEAD'], {
    cwd: ROOT,
    encoding: 'utf8',
  })
  return result.status === 0 ? result.stdout.trim() : 'unknown'
}

function checkAssets() {
  if (!existsSync(MANIFEST_PATH)) throw new Error(`Missing ${MANIFEST_PATH}`)
  const manifest = JSON.parse(readFileSync(MANIFEST_PATH, 'utf8'))
  if (manifest.schema_version !== 1) throw new Error('Unsupported capture manifest schema')
  if (manifest.viewport?.width !== WIDTH || manifest.viewport?.height !== HEIGHT) {
    throw new Error(`Capture viewport must remain ${WIDTH}x${HEIGHT}`)
  }
  const expected = new Set(CAPTURES.map((capture) => capture.file))
  for (const capture of manifest.captures ?? []) {
    if (!expected.delete(capture.file)) throw new Error(`Unexpected capture ${capture.file}`)
    const definition = CAPTURES.find((item) => item.file === capture.file)
    if (
      capture.route !== definition.route
      || capture.ready !== definition.ready
      || (capture.scroll_target ?? null) !== (definition.scrollTarget ?? null)
    ) {
      throw new Error(`${capture.file}: capture contract drift`)
    }
    const path = join(OUTPUT_DIR, capture.file)
    if (!existsSync(path)) throw new Error(`Missing capture asset ${path}`)
    const data = readFileSync(path)
    if (data.length !== capture.bytes) throw new Error(`${capture.file}: byte count drift`)
    if (sha256(data) !== capture.sha256) throw new Error(`${capture.file}: sha256 drift`)
    if (data.length > MAX_ASSET_BYTES) {
      throw new Error(`${capture.file}: ${data.length} bytes exceeds ${MAX_ASSET_BYTES}`)
    }
    const dimensions = webpDimensions(data)
    if (dimensions.width !== WIDTH || dimensions.height !== HEIGHT) {
      throw new Error(`${capture.file}: expected ${WIDTH}x${HEIGHT}, got ${dimensions.width}x${dimensions.height}`)
    }
  }
  if (expected.size > 0) throw new Error(`Manifest missing: ${[...expected].join(', ')}`)
  process.stdout.write(`landing captures: 3 assets verified (${WIDTH}x${HEIGHT}, <=256 KiB each)\n`)
}

function findChrome() {
  const candidates = [
    process.env.CHROME,
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ].filter(Boolean)
  const found = candidates.find(existsSync)
  if (!found) throw new Error('Could not locate Chrome; set CHROME to a Chromium executable')
  return found
}

class CDP {
  constructor(url) {
    this.socket = new WebSocket(url)
    this.sequence = 0
    this.pending = new Map()
    this.listeners = new Set()
    this.ready = new Promise((resolveReady, rejectReady) => {
      this.socket.addEventListener('open', resolveReady)
      this.socket.addEventListener('error', rejectReady)
    })
    this.socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data)
      if (message.id != null && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id)
        this.pending.delete(message.id)
        if (message.error) pending.reject(new Error(message.error.message))
        else pending.resolve(message.result)
      } else if (message.method) {
        for (const listener of this.listeners) listener(message)
      }
    })
  }

  send(method, params = {}) {
    const id = ++this.sequence
    return new Promise((resolveSend, rejectSend) => {
      this.pending.set(id, { resolve: resolveSend, reject: rejectSend })
      this.socket.send(JSON.stringify({ id, method, params }))
    })
  }

  on(listener) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  close() {
    this.socket.close()
  }
}

async function spawnChrome() {
  const profile = mkdtempSync(join(tmpdir(), 'eamos-landing-captures-'))
  const process = spawn(
    findChrome(),
    [
      '--headless=new',
      '--disable-gpu',
      '--no-first-run',
      '--no-default-browser-check',
      '--remote-debugging-address=127.0.0.1',
      '--remote-debugging-port=0',
      `--user-data-dir=${profile}`,
      'about:blank',
    ],
    { stdio: ['ignore', 'ignore', 'pipe'] },
  )
  const port = await new Promise((resolvePort, rejectPort) => {
    const timer = setTimeout(() => rejectPort(new Error('Chrome boot timed out')), TIMEOUT_MS)
    const onData = (chunk) => {
      const match = String(chunk).match(/DevTools listening on ws:\/\/[^:]+:(\d+)\//)
      if (!match) return
      clearTimeout(timer)
      process.stderr.off('data', onData)
      resolvePort(Number.parseInt(match[1], 10))
    }
    process.stderr.on('data', onData)
    process.on('exit', (code) => rejectPort(new Error(`Chrome exited early (${code})`)))
  })
  return {
    port,
    cleanup() {
      process.kill()
      try {
        rmSync(profile, { recursive: true, force: true })
      } catch {
        // Chrome can briefly hold profile files after SIGTERM. The OS temp
        // sweeper can finish that cleanup; never mask the capture result.
      }
    },
  }
}

async function openTab(port) {
  for (const method of ['PUT', 'GET']) {
    const response = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method })
    if (response.ok) return response.json()
  }
  throw new Error('Could not open a Chrome tab')
}

async function waitFor(cdp, expression, label) {
  const deadline = Date.now() + TIMEOUT_MS
  while (Date.now() < deadline) {
    const result = await cdp.send('Runtime.evaluate', {
      expression: `Boolean(${expression})`,
      returnByValue: true,
    })
    if (result?.result?.value === true) return
    await new Promise((resolveWait) => setTimeout(resolveWait, 250))
  }
  throw new Error(`Timed out waiting for ${label}`)
}

async function navigate(cdp, url, ready, scrollTarget = null) {
  await cdp.send('Page.navigate', { url })
  await waitFor(cdp, ready, url)
  const positionPage = scrollTarget
    ? `const target = document.querySelector(${JSON.stringify(scrollTarget)});
       target?.scrollIntoView({ block: 'start', behavior: 'instant' });
       window.scrollBy(0, -72);`
    : 'window.scrollTo(0, 0);'
  await cdp.send('Runtime.evaluate', {
    expression: `
      (async () => {
        await Promise.race([
          Promise.all([
            document.fonts.ready,
            ...Array.from(document.images).map((image) =>
              image.complete ? null : new Promise((resolve) => {
                image.addEventListener('load', resolve, { once: true });
                image.addEventListener('error', resolve, { once: true });
              })
            ),
          ]),
          new Promise((resolve) => setTimeout(resolve, 5000)),
        ]);
        const style = document.createElement('style');
        style.dataset.captureStyle = 'true';
        style.textContent = '*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}';
        document.head.appendChild(style);
        ${positionPage}
        await new Promise((resolve) => setTimeout(resolve, 700));
      })()
    `,
    awaitPromise: true,
  })
}

async function seedCompare(cdp) {
  // Build the same one-source stash as the landing Sample VCF action, directly
  // from the tracked fixture so capture generation cannot drift from it.
  const source = readFileSync(SAMPLE_VCF_PATH, 'utf8')
  const literal = source.match(/export const SAMPLE_VCF = `([\s\S]*?)`/)
  if (!literal) throw new Error(`Could not read SAMPLE_VCF from ${SAMPLE_VCF_PATH}`)
  const variants = literal[1]
    .split(/\r?\n/)
    .filter((line) => line.trim() && !line.startsWith('#'))
    .map((line) => {
      const [chrom, pos, , ref, alt, , filter] = line.split(/\s+/)
      return {
        raw: line,
        gene: null,
        variant: null,
        query: `${chrom}-${pos}-${ref}-${alt}`,
        chrom,
        pos: Number(pos),
        ref,
        alt,
        filter,
        info_af: null,
      }
    })
  const sampleSource = {
    id: 'capture-sample-vcf',
    name: 'sample.vcf',
    kind: 'file',
    variants,
  }
  const stash = {
    savedAt: Date.now(),
    source: 'sample.vcf',
    variants,
    sources: [sampleSource],
  }
  await cdp.send('Page.navigate', { url: `${BASE_URL}/compare` })
  await waitFor(cdp, `location.pathname === '/compare'`, 'compare origin')
  await cdp.send('Runtime.evaluate', {
    expression: `sessionStorage.setItem('eamos.compare.v1', ${JSON.stringify(JSON.stringify(stash))})`,
  })
}

async function captureAll() {
  const response = await fetch(BASE_URL)
  if (!response.ok) throw new Error(`Eamos server returned HTTP ${response.status} at ${BASE_URL}`)
  mkdirSync(OUTPUT_DIR, { recursive: true })
  const chrome = await spawnChrome()
  const tab = await openTab(chrome.port)
  const cdp = new CDP(tab.webSocketDebuggerUrl)
  const consoleErrors = []
  cdp.on((event) => {
    if (event.method === 'Runtime.exceptionThrown') {
      consoleErrors.push(event.params?.exceptionDetails?.exception?.description ?? 'Runtime exception')
    }
  })

  try {
    await cdp.ready
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: WIDTH,
      height: HEIGHT,
      deviceScaleFactor: 1,
      mobile: false,
    })
    const manifestCaptures = []
    for (const capture of CAPTURES) {
      if (capture.id === 'compare') await seedCompare(cdp)
      await navigate(cdp, `${BASE_URL}${capture.route}`, capture.ready, capture.scrollTarget)
      const screenshot = await cdp.send('Page.captureScreenshot', {
        format: 'webp',
        quality: QUALITY,
        fromSurface: true,
        captureBeyondViewport: false,
      })
      const data = Buffer.from(screenshot.data, 'base64')
      if (data.length > MAX_ASSET_BYTES) {
        throw new Error(`${capture.file} is ${data.length} bytes; lower quality below 256 KiB`)
      }
      const path = join(OUTPUT_DIR, capture.file)
      writeFileSync(path, data)
      manifestCaptures.push({
        id: capture.id,
        file: capture.file,
        route: capture.route,
        ready: capture.ready,
        scroll_target: capture.scrollTarget ?? null,
        bytes: statSync(path).size,
        sha256: sha256(data),
      })
      process.stdout.write(`captured ${capture.file} (${data.length} bytes)\n`)
    }

    if (consoleErrors.length > 0) {
      throw new Error(`Browser runtime errors:\n${consoleErrors.join('\n')}`)
    }

    const manifest = {
      schema_version: 1,
      captured_at: new Date().toISOString(),
      source_revision: gitRevision(),
      fixture_policy: 'Bundled demo or offline-safe data only; no patient records.',
      viewport: { width: WIDTH, height: HEIGHT, device_scale_factor: 1 },
      captures: manifestCaptures,
    }
    writeFileSync(MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`)
    checkAssets()
  } finally {
    cdp.close()
    chrome.cleanup()
  }
}

async function captureLandingPreview(
  outputPath,
  selector = '#features article',
  activeStep = null,
  width = WIDTH,
  height = HEIGHT,
) {
  const response = await fetch(BASE_URL)
  if (!response.ok) throw new Error(`Eamos server returned HTTP ${response.status} at ${BASE_URL}`)
  const chrome = await spawnChrome()
  const tab = await openTab(chrome.port)
  const cdp = new CDP(tab.webSocketDebuggerUrl)
  try {
    await cdp.ready
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: false,
    })
    await navigate(
      cdp,
      `${BASE_URL}/`,
      `document.querySelector(${JSON.stringify(selector)}) !== null`,
      selector,
    )
    if (activeStep) {
      const clicked = await cdp.send('Runtime.evaluate', {
        expression: `(() => {
          const label = ${JSON.stringify(activeStep)}.toLowerCase();
          const button = Array.from(document.querySelectorAll('.hero-variant-step'))
            .find((item) => item.textContent.toLowerCase().includes(label));
          if (!button) return false;
          button.click();
          return true;
        })()`,
        returnByValue: true,
      })
      if (clicked?.result?.value !== true) throw new Error(`Hero step not found: ${activeStep}`)
      await waitFor(
        cdp,
        `document.querySelector('.hero-variant-marker small')?.textContent.toLowerCase() === ${JSON.stringify(activeStep.toLowerCase())}`,
        `hero ${activeStep} interaction`,
      )
    }
    await cdp.send('Runtime.evaluate', {
      expression: `Array.from(document.querySelectorAll('#features article')).forEach((item) => {
        item.style.opacity = '1';
        item.style.transform = 'none';
      });
      Array.from(document.querySelectorAll('.hero-dna-strand')).forEach((item) => {
        item.style.strokeDashoffset = '0';
      })`,
    })
    const screenshot = await cdp.send('Page.captureScreenshot', {
      format: 'png',
      fromSurface: true,
      captureBeyondViewport: false,
    })
    const absolute = resolve(outputPath)
    mkdirSync(dirname(absolute), { recursive: true })
    writeFileSync(absolute, Buffer.from(screenshot.data, 'base64'))
    process.stdout.write(`landing preview: ${absolute}\n`)
  } finally {
    cdp.close()
    chrome.cleanup()
  }
}

if (args.check === 'true') {
  try {
    checkAssets()
  } catch (error) {
    process.stderr.write(`landing captures: ${error.message}\n`)
    process.exitCode = 1
  }
} else if (args['preview-landing']) {
  await captureLandingPreview(
    args['preview-landing'],
    args['preview-selector'],
    args['preview-step'],
    Number.parseInt(args['preview-width'] ?? WIDTH, 10),
    Number.parseInt(args['preview-height'] ?? HEIGHT, 10),
  )
} else {
  await captureAll()
}
