#!/usr/bin/env node

// Reproducible browser captures for the landing-page feature section.
// Run a local Eamos web server first, then:
//   node scripts/eamos-capture-landing-features.mjs --base-url=http://127.0.0.1:3001
//   node scripts/eamos-capture-landing-features.mjs --check
//   node scripts/eamos-capture-landing-features.mjs --verify-hero --base-url=http://127.0.0.1:3001
//   node scripts/eamos-capture-landing-features.mjs --verify-pass4 --base-url=http://127.0.0.1:3001

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
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUTPUT_DIR = join(ROOT, 'app', 'web', 'public', 'features')
const MANIFEST_PATH = join(OUTPUT_DIR, 'capture-manifest.json')
const SAMPLE_VCF_PATH = join(ROOT, 'app', 'web', 'lib', 'sample-vcf.ts')
const WIDTH = 1440
const HEIGHT = 960
const QUALITY = 72
const MAX_ASSET_BYTES = 256 * 1024
const TIMEOUT_MS = 30_000
const SOCIAL_CARD_WIDTH = 1200
const SOCIAL_CARD_HEIGHT = 630
const SOCIAL_CARD_SOURCE_PATH = join(ROOT, 'scripts', 'assets', 'landing-social-card.svg')
const SOCIAL_CARD_PATH = join(ROOT, 'app', 'web', 'public', 'og-image.png')
const SOCIAL_CARD_MANIFEST_PATH = join(ROOT, 'scripts', 'assets', 'landing-social-card.manifest.json')
const LANDING_VIEWPORTS = [
  { width: 360, height: 800, hero: 'compact' },
  { width: 390, height: 844, hero: 'compact' },
  { width: 768, height: 1024, hero: 'compact' },
  { width: 1024, height: 768, hero: 'interactive' },
  { width: 1440, height: 960, hero: 'interactive' },
  { width: 1920, height: 1080, hero: 'interactive' },
]
const LANDING_BUDGETS = Object.freeze({
  lcpMs: 2_500,
  cls: 0.1,
  featureBytes: 192 * 1024,
  scriptBytes: 460 * 1024,
  socialCardBytes: 96 * 1024,
})

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

function pngDimensions(buffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])
  if (buffer.length < 24 || !buffer.subarray(0, 8).equals(signature)) {
    throw new Error('not a PNG payload')
  }
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) }
}

function gitRevision() {
  const result = spawnSync('git', ['rev-parse', '--short=12', 'HEAD'], {
    cwd: ROOT,
    encoding: 'utf8',
  })
  return result.status === 0 ? result.stdout.trim() : 'unknown'
}

function checkSocialCard() {
  for (const path of [SOCIAL_CARD_SOURCE_PATH, SOCIAL_CARD_PATH, SOCIAL_CARD_MANIFEST_PATH]) {
    if (!existsSync(path)) throw new Error(`Missing social-card artifact ${path}`)
  }
  const source = readFileSync(SOCIAL_CARD_SOURCE_PATH)
  const sourceText = source.toString('utf8')
  for (const phrase of ['FREE ACCESS', 'Trace a genetic', '11 predictor', 'RESEARCH USE ONLY']) {
    if (!sourceText.includes(phrase)) throw new Error(`Social card is missing positioning phrase: ${phrase}`)
  }
  const card = readFileSync(SOCIAL_CARD_PATH)
  const manifest = JSON.parse(readFileSync(SOCIAL_CARD_MANIFEST_PATH, 'utf8'))
  if (manifest.schema_version !== 1) throw new Error('Unsupported social-card manifest schema')
  if (
    manifest.source !== 'scripts/assets/landing-social-card.svg'
    || manifest.output !== 'app/web/public/og-image.png'
    || manifest.width !== SOCIAL_CARD_WIDTH
    || manifest.height !== SOCIAL_CARD_HEIGHT
  ) {
    throw new Error('Social-card manifest contract drift')
  }
  if (manifest.source_sha256 !== sha256(source)) throw new Error('Social-card source sha256 drift')
  if (manifest.output_sha256 !== sha256(card)) throw new Error('Social-card output sha256 drift')
  if (manifest.bytes !== card.length) throw new Error('Social-card byte count drift')
  if (card.length > LANDING_BUDGETS.socialCardBytes) {
    throw new Error(`Social card is ${card.length} bytes; budget is ${LANDING_BUDGETS.socialCardBytes}`)
  }
  const dimensions = pngDimensions(card)
  if (dimensions.width !== SOCIAL_CARD_WIDTH || dimensions.height !== SOCIAL_CARD_HEIGHT) {
    throw new Error(
      `Social card must be ${SOCIAL_CARD_WIDTH}x${SOCIAL_CARD_HEIGHT}, got ${dimensions.width}x${dimensions.height}`,
    )
  }
  return card.length
}

function checkAssets() {
  if (!existsSync(MANIFEST_PATH)) throw new Error(`Missing ${MANIFEST_PATH}`)
  const manifest = JSON.parse(readFileSync(MANIFEST_PATH, 'utf8'))
  if (manifest.schema_version !== 1) throw new Error('Unsupported capture manifest schema')
  if (manifest.viewport?.width !== WIDTH || manifest.viewport?.height !== HEIGHT) {
    throw new Error(`Capture viewport must remain ${WIDTH}x${HEIGHT}`)
  }
  const expected = new Set(CAPTURES.map((capture) => capture.file))
  let totalBytes = 0
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
    totalBytes += data.length
    const dimensions = webpDimensions(data)
    if (dimensions.width !== WIDTH || dimensions.height !== HEIGHT) {
      throw new Error(`${capture.file}: expected ${WIDTH}x${HEIGHT}, got ${dimensions.width}x${dimensions.height}`)
    }
  }
  if (expected.size > 0) throw new Error(`Manifest missing: ${[...expected].join(', ')}`)
  if (totalBytes > LANDING_BUDGETS.featureBytes) {
    throw new Error(
      `Landing captures total ${totalBytes} bytes; budget is ${LANDING_BUDGETS.featureBytes}`,
    )
  }
  const socialCardBytes = checkSocialCard()
  process.stdout.write(
    `landing assets: 3 captures ${totalBytes} bytes; social card ${socialCardBytes} bytes (${SOCIAL_CARD_WIDTH}x${SOCIAL_CARD_HEIGHT})\n`,
  )
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

async function generateSocialCard() {
  if (!existsSync(SOCIAL_CARD_SOURCE_PATH)) {
    throw new Error(`Missing social-card source ${SOCIAL_CARD_SOURCE_PATH}`)
  }
  const chrome = await spawnChrome()
  const tab = await openTab(chrome.port)
  const cdp = new CDP(tab.webSocketDebuggerUrl)
  try {
    await cdp.ready
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: SOCIAL_CARD_WIDTH,
      height: SOCIAL_CARD_HEIGHT,
      deviceScaleFactor: 1,
      mobile: false,
    })
    await cdp.send('Page.navigate', { url: pathToFileURL(SOCIAL_CARD_SOURCE_PATH).href })
    await waitFor(
      cdp,
      `document.documentElement?.tagName.toLowerCase() === 'svg'
        && document.documentElement.getBoundingClientRect().width === ${SOCIAL_CARD_WIDTH}`,
      'social-card SVG',
    )
    await evaluateValue(
      cdp,
      `(async () => {
        await document.fonts.ready;
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        return true;
      })()`,
    )
    const screenshot = await cdp.send('Page.captureScreenshot', {
      format: 'png',
      fromSurface: true,
      captureBeyondViewport: false,
    })
    const data = Buffer.from(screenshot.data, 'base64')
    writeFileSync(SOCIAL_CARD_PATH, data)
    const source = readFileSync(SOCIAL_CARD_SOURCE_PATH)
    const manifest = {
      schema_version: 1,
      source: 'scripts/assets/landing-social-card.svg',
      output: 'app/web/public/og-image.png',
      width: SOCIAL_CARD_WIDTH,
      height: SOCIAL_CARD_HEIGHT,
      bytes: data.length,
      source_sha256: sha256(source),
      output_sha256: sha256(data),
    }
    writeFileSync(SOCIAL_CARD_MANIFEST_PATH, `${JSON.stringify(manifest, null, 2)}\n`)
    const bytes = checkSocialCard()
    process.stdout.write(`landing social card: generated ${SOCIAL_CARD_WIDTH}x${SOCIAL_CARD_HEIGHT} (${bytes} bytes)\n`)
  } finally {
    cdp.close()
    chrome.cleanup()
  }
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

function assertBrowser(value, message) {
  if (!value) throw new Error(`Landing hero regression: ${message}`)
}

async function evaluateValue(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  })
  if (result?.exceptionDetails) {
    throw new Error(
      result.exceptionDetails.exception?.description
        ?? result.exceptionDetails.text
        ?? 'browser evaluation failed',
    )
  }
  return result?.result?.value
}

async function pressKey(cdp, key, code, windowsVirtualKeyCode, modifiers = 0) {
  const text = key === 'Enter' ? '\r' : key === ' ' ? ' ' : undefined
  const params = {
    key,
    code,
    windowsVirtualKeyCode,
    nativeVirtualKeyCode: windowsVirtualKeyCode,
    modifiers,
    ...(text ? { text, unmodifiedText: text } : {}),
  }
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', ...params })
  await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', ...params })
}

async function clickSelector(cdp, selector) {
  const point = await evaluateValue(
    cdp,
    `(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    })()`,
  )
  assertBrowser(point, `mouse target not found: ${selector}`)
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: point.x, y: point.y })
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: point.x,
    y: point.y,
    button: 'left',
    clickCount: 1,
  })
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: point.x,
    y: point.y,
    button: 'left',
    clickCount: 1,
  })
}

async function heroSnapshot(cdp) {
  return evaluateValue(
    cdp,
    `(() => {
      const marker = document.querySelector('.hero-variant-marker');
      const readout = document.querySelector('#hero-variant-readout');
      const activeElement = document.activeElement;
      const activeStyle = activeElement ? getComputedStyle(activeElement) : null;
      return {
        markerLabel: marker?.getAttribute('aria-label') ?? '',
        markerView: marker?.querySelector('small')?.textContent?.trim() ?? '',
        readout: readout?.textContent?.replace(/\\s+/g, ' ').trim() ?? '',
        readoutRole: readout?.getAttribute('role') ?? '',
        readoutLive: readout?.getAttribute('aria-live') ?? '',
        readoutAtomic: readout?.getAttribute('aria-atomic') ?? '',
        pressed: Array.from(document.querySelectorAll('.hero-variant-step'))
          .map((button) => button.getAttribute('aria-pressed')),
        activeText: activeElement?.textContent?.replace(/\\s+/g, ' ').trim() ?? '',
        activeClass: activeElement?.className ?? '',
        focusVisible: activeElement?.matches?.(':focus-visible') ?? false,
        outlineStyle: activeStyle?.outlineStyle ?? '',
        outlineWidth: activeStyle?.outlineWidth ?? '',
      };
    })()`,
  )
}

async function verifyHeroInTab(cdp) {
  await cdp.send('Emulation.setEmulatedMedia', {
    media: 'screen',
    features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }],
  })
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: WIDTH,
    height: HEIGHT,
    deviceScaleFactor: 1,
    mobile: false,
  })
  await cdp.send('Page.navigate', { url: `${BASE_URL}/` })
  await waitFor(
    cdp,
    `document.querySelectorAll('.hero-variant-step').length === 4
      && document.querySelector('.hero-variant-marker')?.getClientRects().length === 1`,
    'desktop landing hero',
  )

  const initial = await heroSnapshot(cdp)
  assertBrowser(initial.markerView === 'Transcript', 'the bundled transcript view is not the initial state')
  assertBrowser(initial.readout.includes('NM_000329.3') && initial.readout.includes('RPE65 c.260A>G'), 'initial transcript identity drifted')
  assertBrowser(initial.readoutRole === 'status' && initial.readoutLive === 'polite' && initial.readoutAtomic === 'true', 'readout is not an atomic polite status')
  assertBrowser(initial.pressed.join(',') === 'false,true,false,false', 'initial aria-pressed state is not singular')

  const axTree = await cdp.send('Accessibility.getFullAXTree')
  const buttonNames = (axTree.nodes ?? [])
    .filter((node) => node.role?.value === 'button')
    .map((node) => node.name?.value ?? '')
  for (const name of ['01 Genomic', '02 Transcript', '03 Protein', '04 Evidence']) {
    assertBrowser(buttonNames.includes(name), `accessible button name missing: ${name}`)
  }
  assertBrowser(
    buttonNames.some((name) => name.includes('Current view: Transcript') && name.includes('Show next representation')),
    'the locus control has no descriptive accessible name',
  )

  await clickSelector(cdp, '.hero-variant-step:nth-child(1)')
  await waitFor(
    cdp,
    `document.querySelector('.hero-variant-marker small')?.textContent === 'Genomic'`,
    'mouse-selected genomic hero view',
  )
  const mouseState = await heroSnapshot(cdp)
  assertBrowser(mouseState.pressed.join(',') === 'true,false,false,false', 'mouse selection did not update aria-pressed')
  assertBrowser(mouseState.readout.includes('GRCh38') && mouseState.readout.includes('chr1:68,444,869 T>C'), 'mouse selection did not update the announced readout')

  await pressKey(cdp, 'Tab', 'Tab', 9)
  await pressKey(cdp, 'Tab', 'Tab', 9)
  const keyboardFocus = await heroSnapshot(cdp)
  assertBrowser(keyboardFocus.activeText.includes('Protein'), 'Tab order did not reach the Protein control')
  assertBrowser(keyboardFocus.focusVisible, 'keyboard focus does not match :focus-visible')
  assertBrowser(keyboardFocus.outlineStyle !== 'none' && Number.parseFloat(keyboardFocus.outlineWidth) >= 2, 'keyboard focus has no visible outline')
  await pressKey(cdp, 'Enter', 'Enter', 13)
  await waitFor(
    cdp,
    `document.querySelector('.hero-variant-marker small')?.textContent === 'Protein'`,
    'keyboard-selected protein hero view',
  )
  const keyboardState = await heroSnapshot(cdp)
  assertBrowser(keyboardState.pressed.join(',') === 'false,false,true,false', 'keyboard selection did not update aria-pressed')
  assertBrowser(keyboardState.readout.includes('p.Asp87Gly'), 'keyboard selection did not update the announced readout')

  await pressKey(cdp, 'Tab', 'Tab', 9, 8)
  await pressKey(cdp, 'Tab', 'Tab', 9, 8)
  await pressKey(cdp, 'Tab', 'Tab', 9, 8)
  const markerFocus = await heroSnapshot(cdp)
  assertBrowser(String(markerFocus.activeClass).includes('hero-variant-marker'), 'reverse Tab order did not reach the locus control')
  assertBrowser(markerFocus.focusVisible, 'locus control has no keyboard focus-visible state')
  await pressKey(cdp, ' ', 'Space', 32)
  await waitFor(
    cdp,
    `document.querySelector('.hero-variant-marker small')?.textContent === 'Evidence'`,
    'keyboard-cycled evidence hero view',
  )
  const cycledState = await heroSnapshot(cdp)
  assertBrowser(cycledState.pressed.join(',') === 'false,false,false,true', 'locus keyboard cycle did not update aria-pressed')
  assertBrowser(cycledState.readout.includes('11 predictor engines'), 'locus keyboard cycle did not announce the evidence view')

  await cdp.send('Emulation.setEmulatedMedia', {
    media: 'screen',
    features: [{ name: 'prefers-reduced-motion', value: 'reduce' }],
  })
  await waitFor(
    cdp,
    `getComputedStyle(document.querySelector('.hero-dna-strand')).animationName === 'none'`,
    'reduced-motion hero state',
  )
  const reduced = await evaluateValue(
    cdp,
    `(() => {
      const strand = getComputedStyle(document.querySelector('.hero-dna-strand'));
      const marker = getComputedStyle(document.querySelector('.hero-variant-marker'));
      const step = getComputedStyle(document.querySelector('.hero-variant-step'));
      return {
        animationName: strand.animationName,
        strokeDashoffset: strand.strokeDashoffset,
        markerTransitionSeconds: marker.transitionDuration
          .split(',').map((value) => Number.parseFloat(value) * (value.includes('ms') ? 0.001 : 1)),
        stepTransitionSeconds: step.transitionDuration
          .split(',').map((value) => Number.parseFloat(value) * (value.includes('ms') ? 0.001 : 1)),
      };
    })()`,
  )
  assertBrowser(reduced.animationName === 'none' && Number.parseFloat(reduced.strokeDashoffset) === 0, 'reduced motion does not render a fully drawn static strand')
  assertBrowser([...reduced.markerTransitionSeconds, ...reduced.stepTransitionSeconds].every((value) => value <= 0.001), 'reduced motion leaves a visible transition')

  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  })
  const mobileHidden = await evaluateValue(
    cdp,
    `(() => {
      const hero = document.querySelector('.hero-variant-map')?.closest('aside');
      return hero != null && getComputedStyle(hero).display === 'none' && hero.getClientRects().length === 0;
    })()`,
  )
  assertBrowser(mobileHidden, 'desktop instrument remains visible in the compact mobile hero')

  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: WIDTH,
    height: HEIGHT,
    deviceScaleFactor: 1,
    mobile: false,
  })
  await cdp.send('Emulation.setEmulatedMedia', {
    media: 'screen',
    features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }],
  })
  process.stdout.write('landing hero: mouse, keyboard, accessibility, reduced motion, and mobile contract verified\n')
}

function assertLanding(value, message) {
  if (!value) throw new Error(`Landing Pass 3 regression: ${message}`)
}

function featureAssetBytes() {
  return CAPTURES.reduce((total, capture) => total + statSync(join(OUTPUT_DIR, capture.file)).size, 0)
}

async function installPerformanceObservers(cdp) {
  await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
    source: `(() => {
      window.__eamosLandingPerformance = { lcp: 0, lcpElement: '', cls: 0 };
      try {
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            window.__eamosLandingPerformance.lcp = Math.max(
              window.__eamosLandingPerformance.lcp,
              entry.startTime,
            );
            const element = entry.element;
            window.__eamosLandingPerformance.lcpElement = element
              ? [element.tagName.toLowerCase(), element.id && '#' + element.id, element.className && '.' + String(element.className).trim().replace(/\\s+/g, '.')]
                  .filter(Boolean).join('')
              : '';
          }
        }).observe({ type: 'largest-contentful-paint', buffered: true });
      } catch {}
      try {
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) window.__eamosLandingPerformance.cls += entry.value;
          }
        }).observe({ type: 'layout-shift', buffered: true });
      } catch {}
    })()`,
  })
}

async function measureLandingPerformance(cdp) {
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
  await cdp.send('Network.clearBrowserCache')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: WIDTH,
    height: HEIGHT,
    deviceScaleFactor: 1,
    mobile: false,
  })
  await cdp.send('Page.navigate', { url: `${BASE_URL}/` })
  await waitFor(
    cdp,
    `document.readyState === 'complete'
      && document.querySelector('#hero [role="search"]')
      && document.querySelectorAll('[data-landing-feature-image]').length === 3`,
    'landing performance load',
  )
  await evaluateValue(
    cdp,
    `(async () => {
      await document.fonts.ready;
      await new Promise((resolve) => setTimeout(resolve, 1600));
      return true;
    })()`,
  )
  const metrics = await evaluateValue(
    cdp,
    `(() => {
      const state = window.__eamosLandingPerformance ?? {};
      const scripts = performance.getEntriesByType('resource').filter((entry) =>
        entry.initiatorType === 'script' || new URL(entry.name).pathname.endsWith('.js')
      );
      return {
        lcpMs: Math.round(state.lcp ?? 0),
        lcpElement: state.lcpElement ?? '',
        cls: Number((state.cls ?? 0).toFixed(4)),
        scriptBytes: Math.round(scripts.reduce((sum, entry) => sum + entry.encodedBodySize, 0)),
        scriptTransferBytes: Math.round(scripts.reduce((sum, entry) => sum + entry.transferSize, 0)),
        scriptRequests: scripts.length,
        scriptDetails: scripts
          .map((entry) => ({ path: new URL(entry.name).pathname, bytes: entry.encodedBodySize }))
          .sort((left, right) => right.bytes - left.bytes),
      };
    })()`,
  )
  metrics.featureBytes = featureAssetBytes()
  process.stdout.write(
    `landing performance: LCP ${metrics.lcpMs}ms (${metrics.lcpElement || 'unknown'}), CLS ${metrics.cls.toFixed(4)}, JS ${metrics.scriptBytes} bytes / ${metrics.scriptRequests} requests, captures ${metrics.featureBytes} bytes\n`,
  )
  if (args.verbose === 'true') {
    for (const script of metrics.scriptDetails) {
      process.stdout.write(`  ${script.bytes.toString().padStart(7)}  ${script.path}\n`)
    }
  }

  assertLanding(metrics.lcpMs > 0, 'LCP was not observed')
  assertLanding(metrics.lcpMs <= LANDING_BUDGETS.lcpMs, `LCP ${metrics.lcpMs}ms exceeds ${LANDING_BUDGETS.lcpMs}ms`)
  assertLanding(metrics.cls <= LANDING_BUDGETS.cls, `CLS ${metrics.cls} exceeds ${LANDING_BUDGETS.cls}`)
  assertLanding(metrics.scriptBytes > 0, 'shipped JavaScript bytes were not measurable')
  assertLanding(
    metrics.scriptDetails.every(
      (script) => !/\/(?:posthog-recorder|surveys)\.js$/.test(script.path),
    ),
    'PostHog recorder or survey JavaScript loaded despite the privacy boundary',
  )
  assertLanding(
    metrics.scriptBytes <= LANDING_BUDGETS.scriptBytes,
    `JavaScript ${metrics.scriptBytes} bytes exceeds ${LANDING_BUDGETS.scriptBytes}`,
  )
  assertLanding(
    metrics.featureBytes <= LANDING_BUDGETS.featureBytes,
    `feature captures ${metrics.featureBytes} bytes exceeds ${LANDING_BUDGETS.featureBytes}`,
  )
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: false })
  return metrics
}

async function verifySocialMetadata(cdp) {
  const metadata = await evaluateValue(
    cdp,
    `(() => {
      const property = (name) => document.querySelector('meta[property="' + name + '"]')?.content ?? '';
      const named = (name) => document.querySelector('meta[name="' + name + '"]')?.content ?? '';
      return {
        title: property('og:title'),
        description: property('og:description'),
        image: property('og:image'),
        imageWidth: property('og:image:width'),
        imageHeight: property('og:image:height'),
        imageAlt: property('og:image:alt'),
        twitterCard: named('twitter:card'),
        twitterImage: named('twitter:image'),
        twitterImageAlt: named('twitter:image:alt'),
      };
    })()`,
  )
  assertLanding(/free/i.test(metadata.title), 'Open Graph title does not state free positioning')
  assertLanding(/Free genomic variant evidence/i.test(metadata.description), 'Open Graph description drifted')
  assertLanding(new URL(metadata.image).pathname === '/og-image.png', 'Open Graph image path drifted')
  assertLanding(metadata.imageWidth === String(SOCIAL_CARD_WIDTH), 'Open Graph image width drifted')
  assertLanding(metadata.imageHeight === String(SOCIAL_CARD_HEIGHT), 'Open Graph image height drifted')
  assertLanding(/free genomic variant evidence/i.test(metadata.imageAlt), 'Open Graph image alt text drifted')
  assertLanding(metadata.twitterCard === 'summary_large_image', 'Twitter card type drifted')
  assertLanding(new URL(metadata.twitterImage).pathname === '/og-image.png', 'Twitter image path drifted')
  assertLanding(/free genomic variant evidence/i.test(metadata.twitterImageAlt), 'Twitter image alt text drifted')

  const response = await fetch(`${BASE_URL}/og-image.png`)
  assertLanding(response.ok, `social-card request returned HTTP ${response.status}`)
  assertLanding(response.headers.get('content-type')?.startsWith('image/png'), 'social card is not served as image/png')
  const card = Buffer.from(await response.arrayBuffer())
  const dimensions = pngDimensions(card)
  assertLanding(
    dimensions.width === SOCIAL_CARD_WIDTH && dimensions.height === SOCIAL_CARD_HEIGHT,
    'served social-card dimensions drifted',
  )
  assertLanding(sha256(card) === sha256(readFileSync(SOCIAL_CARD_PATH)), 'served social-card bytes drifted')
  process.stdout.write('landing metadata: Open Graph and Twitter 1200x630 preview contract verified\n')
}

async function focusSnapshot(cdp) {
  return evaluateValue(
    cdp,
    `(() => {
      const element = document.activeElement;
      if (!element || element === document.body) return null;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {
        name: element.getAttribute('aria-label')
          || element.textContent?.replace(/\\s+/g, ' ').trim()
          || element.getAttribute('placeholder')
          || element.tagName.toLowerCase(),
        tag: element.tagName.toLowerCase(),
        opacity: Number.parseFloat(style.opacity),
        displayed: style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0,
        inViewport: rect.right > 0 && rect.left < innerWidth && rect.bottom > 0 && rect.top < innerHeight,
        inHorizontalBounds: rect.left >= -1 && rect.right <= innerWidth + 1,
        inert: element.closest('[inert]') !== null,
        ariaHidden: element.closest('[aria-hidden="true"]') !== null,
        focusVisible: element.matches(':focus-visible'),
      };
    })()`,
  )
}

async function verifyKeyboardOrder(cdp, width) {
  await evaluateValue(
    cdp,
    `(() => {
      window.scrollTo(0, 0);
      const home = document.querySelector('[data-landing-nav] a[aria-label="Eamos home"]');
      home?.focus();
      return document.activeElement === home;
    })()`,
  )
  const snapshots = []
  for (let index = 0; index < 9; index += 1) {
    await pressKey(cdp, 'Tab', 'Tab', 9)
    const snapshot = await focusSnapshot(cdp)
    assertLanding(snapshot, `${width}px keyboard sequence lost focus at step ${index + 1}`)
    snapshots.push(snapshot)
  }
  for (const [index, snapshot] of snapshots.entries()) {
    assertLanding(snapshot.displayed && snapshot.opacity > 0.01, `${width}px keyboard target ${index + 1} is visually hidden (${snapshot.name})`)
    assertLanding(snapshot.inViewport && snapshot.inHorizontalBounds, `${width}px keyboard target ${index + 1} is clipped (${snapshot.name})`)
    assertLanding(!snapshot.inert && !snapshot.ariaHidden, `${width}px keyboard target ${index + 1} is inert or aria-hidden (${snapshot.name})`)
    assertLanding(snapshot.focusVisible, `${width}px keyboard target ${index + 1} does not match :focus-visible (${snapshot.name})`)
  }
  const names = snapshots.map((snapshot) => snapshot.name)
  assertLanding(!names.includes('Back to top'), `${width}px hidden back-to-top control remains in initial tab order`)
  assertLanding(
    names.includes('Search a gene and variant, or ask a question'),
    `${width}px initial keyboard order does not reach the primary search`,
  )
  return names
}

async function verifyFeatureCrops(cdp, width) {
  const images = await evaluateValue(cdp, `document.querySelectorAll('[data-landing-feature-image]').length`)
  assertLanding(images === CAPTURES.length, `${width}px feature-image count drifted`)
  for (let index = 0; index < images; index += 1) {
    await evaluateValue(
      cdp,
      `document.querySelectorAll('[data-landing-feature-image]')[${index}]?.scrollIntoView({ block: 'center' })`,
    )
    await waitFor(
      cdp,
      `(() => {
        const image = document.querySelectorAll('[data-landing-feature-image]')[${index}];
        return image?.complete && image.naturalWidth === ${WIDTH} && image.naturalHeight === ${HEIGHT};
      })()`,
      `${width}px feature image ${index + 1}`,
    )
    const state = await evaluateValue(
      cdp,
      `(() => {
        const image = document.querySelectorAll('[data-landing-feature-image]')[${index}];
        const frame = image.closest('figure').querySelector('.relative');
        const imageRect = image.getBoundingClientRect();
        const frameRect = frame.getBoundingClientRect();
        return {
          imageWidth: imageRect.width,
          imageHeight: imageRect.height,
          frameWidth: frameRect.width,
          frameHeight: frameRect.height,
          frameLeft: frameRect.left,
          frameRight: frameRect.right,
          objectFit: getComputedStyle(image).objectFit,
          objectPosition: getComputedStyle(image).objectPosition,
          overflow: document.scrollingElement.scrollWidth - innerWidth,
        };
      })()`,
    )
    assertLanding(state.frameWidth > 0 && state.frameHeight > 0, `${width}px feature crop ${index + 1} collapsed`)
    assertLanding(Math.abs(state.frameWidth / state.frameHeight - 1.5) < 0.02, `${width}px feature crop ${index + 1} lost its 3:2 ratio`)
    assertLanding(Math.abs(state.imageWidth - state.frameWidth) < 1 && Math.abs(state.imageHeight - state.frameHeight) < 1, `${width}px feature image ${index + 1} does not fill its crop`)
    assertLanding(state.frameLeft >= -1 && state.frameRight <= width + 1, `${width}px feature crop ${index + 1} overflows horizontally`)
    assertLanding(state.objectFit === 'cover' && state.objectPosition === '50% 0%', `${width}px feature crop ${index + 1} positioning drifted`)
    assertLanding(state.overflow <= 1, `${width}px page overflows by ${state.overflow}px at feature ${index + 1}`)
  }
  return images
}

async function verifyResponsiveViewport(cdp, viewport) {
  const { width, height, hero } = viewport
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width <= 390,
  })
  await cdp.send('Page.navigate', { url: `${BASE_URL}/` })
  await waitFor(
    cdp,
    `document.querySelector('[data-landing-nav]')
      && document.querySelector('#hero [role="search"]')
      && document.querySelectorAll('[data-landing-feature-image]').length === 3`,
    `${width}px landing`,
  )
  await evaluateValue(
    cdp,
    `(async () => {
      await document.fonts.ready;
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      window.scrollTo(0, 0);
      return true;
    })()`,
  )

  const initial = await evaluateValue(
    cdp,
    `(() => {
      const nav = document.querySelector('[data-landing-nav]');
      const navRect = nav.getBoundingClientRect();
      const map = document.querySelector('.hero-variant-map')?.closest('aside');
      const mapVisible = map != null && getComputedStyle(map).display !== 'none' && map.getClientRects().length === 1;
      const heroSearch = document.querySelector('#hero [role="search"]')?.getBoundingClientRect();
      const backToTop = document.querySelector('[aria-label="Back to top"]');
      const navLinks = Array.from(document.querySelectorAll('.lnav-link')).filter((link) => link.getClientRects().length > 0);
      const menuToggle = document.querySelector('[aria-label="Open menu"]');
      return {
        innerWidth,
        overflow: document.scrollingElement.scrollWidth - innerWidth,
        navPosition: getComputedStyle(nav).position,
        navLeft: navRect.left,
        navRight: navRect.right,
        mapVisible,
        heroSearchLeft: heroSearch?.left ?? -1,
        heroSearchRight: heroSearch?.right ?? -1,
        backToTopTabIndex: backToTop?.tabIndex ?? 0,
        backToTopHidden: backToTop?.getAttribute('aria-hidden') === 'true',
        navLinkCount: navLinks.length,
        menuVisible: menuToggle != null && menuToggle.getClientRects().length === 1,
      };
    })()`,
  )
  assertLanding(initial.innerWidth === width, `${width}px viewport emulation drifted to ${initial.innerWidth}px`)
  assertLanding(initial.overflow <= 1, `${width}px page overflows horizontally by ${initial.overflow}px`)
  assertLanding(initial.navPosition === 'sticky', `${width}px nav is not sticky`)
  assertLanding(initial.navLeft >= -1 && initial.navRight <= width + 1, `${width}px nav is clipped`)
  assertLanding(initial.heroSearchLeft >= -1 && initial.heroSearchRight <= width + 1, `${width}px hero search is clipped`)
  assertLanding(initial.backToTopTabIndex === -1 && initial.backToTopHidden, `${width}px back-to-top is exposed before it is visible`)
  assertLanding(initial.mapVisible === (hero === 'interactive'), `${width}px hero mode is not ${hero}`)
  assertLanding(initial.navLinkCount === (width >= 768 ? 3 : 0), `${width}px desktop nav-link visibility drifted`)
  assertLanding(initial.menuVisible === (width < 768), `${width}px mobile-menu visibility drifted`)

  if (hero === 'interactive') {
    await evaluateValue(cdp, `document.querySelector('.hero-variant-step:nth-child(4)')?.click()`)
    await waitFor(
      cdp,
      `document.querySelector('.hero-variant-marker small')?.textContent === 'Evidence'
        && document.querySelector('.hero-variant-step:nth-child(4)')?.getAttribute('aria-pressed') === 'true'`,
      `${width}px interactive hero`,
    )
  } else {
    const hiddenControls = await evaluateValue(
      cdp,
      `Array.from(document.querySelectorAll('.hero-variant-step')).filter((button) => button.getClientRects().length > 0).length`,
    )
    assertLanding(hiddenControls === 0, `${width}px compact hero exposes desktop controls`)
  }

  const focusNames = await verifyKeyboardOrder(cdp, width)

  if (width < 768) {
    await evaluateValue(cdp, `document.querySelector('[aria-label="Open menu"]')?.click()`)
    await waitFor(cdp, `document.querySelectorAll('#mobile-nav-menu a').length === 3`, `${width}px mobile menu open`)
    const menu = await evaluateValue(
      cdp,
      `(() => {
        const toggle = document.querySelector('[aria-label="Close menu"]');
        const links = Array.from(document.querySelectorAll('#mobile-nav-menu a'));
        return {
          expanded: toggle?.getAttribute('aria-expanded'),
          visibleLinks: links.filter((link) => {
            const rect = link.getBoundingClientRect();
            return rect.width > 0 && rect.left >= -1 && rect.right <= innerWidth + 1;
          }).length,
        };
      })()`,
    )
    assertLanding(menu.expanded === 'true' && menu.visibleLinks === 3, `${width}px mobile menu is not keyboard-safe`)
    await pressKey(cdp, 'Escape', 'Escape', 27)
    await waitFor(cdp, `document.querySelector('#mobile-nav-menu') === null`, `${width}px mobile menu close`)
  }

  await evaluateValue(cdp, `window.scrollTo(0, 480)`)
  await waitFor(
    cdp,
    `document.querySelector('[aria-label="Back to top"]')?.tabIndex === 0
      && document.querySelector('[aria-label="Back to top"]')?.getAttribute('aria-hidden') !== 'true'`,
    `${width}px sticky-nav handoff`,
  )
  const sticky = await evaluateValue(
    cdp,
    `(() => {
      const nav = document.querySelector('[data-landing-nav]');
      const rect = nav.getBoundingClientRect();
      const compact = nav.querySelector('[role="search"]');
      const compactRect = compact?.getBoundingClientRect();
      return {
        top: rect.top,
        left: rect.left,
        right: rect.right,
        compactVisible: compactRect != null && compactRect.width > 0 && compactRect.height > 0
          && getComputedStyle(compact).opacity !== '0'
          && compact.closest('[inert]') === null,
        overflow: document.scrollingElement.scrollWidth - innerWidth,
      };
    })()`,
  )
  assertLanding(Math.abs(sticky.top) <= 1, `${width}px sticky nav moved to y=${sticky.top}`)
  assertLanding(sticky.left >= -1 && sticky.right <= width + 1, `${width}px sticky nav is clipped after scroll`)
  assertLanding(sticky.compactVisible === (width >= 768), `${width}px compact-nav search visibility drifted`)
  assertLanding(sticky.overflow <= 1, `${width}px page overflows after sticky-nav handoff`)

  const cropCount = await verifyFeatureCrops(cdp, width)
  await evaluateValue(cdp, `window.scrollTo(0, 0)`)
  const screenshot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    fromSurface: true,
    captureBeyondViewport: false,
  })
  const dimensions = pngDimensions(Buffer.from(screenshot.data, 'base64'))
  assertLanding(dimensions.width === width && dimensions.height === height, `${width}px browser screenshot dimensions drifted`)
  process.stdout.write(
    `landing viewport: ${width}x${height} ${hero}, ${cropCount} crops, ${focusNames.length} keyboard targets verified\n`,
  )
}

async function verifyLandingPass3() {
  const response = await fetch(BASE_URL)
  if (!response.ok) throw new Error(`Eamos server returned HTTP ${response.status} at ${BASE_URL}`)
  checkAssets()
  const chrome = await spawnChrome()
  const tab = await openTab(chrome.port)
  const cdp = new CDP(tab.webSocketDebuggerUrl)
  const runtimeErrors = []
  cdp.on((event) => {
    if (event.method === 'Runtime.exceptionThrown') {
      runtimeErrors.push(event.params?.exceptionDetails?.exception?.description ?? 'Runtime exception')
    }
  })
  try {
    await cdp.ready
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Network.enable')
    await cdp.send('Accessibility.enable')
    await cdp.send('Emulation.setEmulatedMedia', {
      media: 'screen',
      features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }],
    })
    await installPerformanceObservers(cdp)
    await measureLandingPerformance(cdp)
    await verifySocialMetadata(cdp)
    for (const viewport of LANDING_VIEWPORTS) await verifyResponsiveViewport(cdp, viewport)
    if (runtimeErrors.length > 0) {
      throw new Error(`Browser runtime errors:\n${runtimeErrors.join('\n')}`)
    }
    process.stdout.write('landing Pass 3: responsive, accessibility, performance, and social preview budgets verified\n')
  } finally {
    cdp.close()
    chrome.cleanup()
  }
}

function assertDiscovery(value, message) {
  if (!value) throw new Error(`Landing Pass 4 regression: ${message}`)
}

async function verifyLandingPass4() {
  const response = await fetch(BASE_URL)
  if (!response.ok) throw new Error(`Eamos server returned HTTP ${response.status} at ${BASE_URL}`)
  const chrome = await spawnChrome()
  const tab = await openTab(chrome.port)
  const cdp = new CDP(tab.webSocketDebuggerUrl)
  const runtimeErrors = []
  const batchRequests = []
  cdp.on((event) => {
    if (event.method === 'Runtime.exceptionThrown') {
      runtimeErrors.push(event.params?.exceptionDetails?.exception?.description ?? 'Runtime exception')
    }
    if (
      event.method === 'Network.requestWillBeSent'
      && new URL(event.params.request.url).pathname.startsWith('/api/v1/batch')
    ) {
      batchRequests.push(event.params.request.url)
    }
  })

  try {
    await cdp.ready
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Network.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: WIDTH,
      height: HEIGHT,
      deviceScaleFactor: 1,
      mobile: false,
    })

    await navigate(
      cdp,
      `${BASE_URL}/`,
      `document.querySelectorAll('[data-share-sample]').length === 2`,
    )
    const sharePaths = await evaluateValue(
      cdp,
      `Array.from(document.querySelectorAll('[data-share-sample]')).map((button) => button.dataset.shareSample)`,
    )
    assertDiscovery(
      JSON.stringify(sharePaths) === JSON.stringify([
        '/report?fixture=rpe65-negative',
        '/compare?demo=1',
      ]),
      `safe share paths drifted: ${JSON.stringify(sharePaths)}`,
    )
    await evaluateValue(
      cdp,
      `(() => {
        window.__eamosCopiedSample = '';
        Object.defineProperty(navigator, 'clipboard', {
          configurable: true,
          value: { writeText: async (value) => { window.__eamosCopiedSample = value; } },
        });
        return true;
      })()`,
    )
    for (const path of sharePaths) {
      const selector = `[data-share-sample=${JSON.stringify(path)}]`
      await evaluateValue(cdp, `document.querySelector(${JSON.stringify(selector)})?.scrollIntoView({ block: 'center' })`)
      await clickSelector(cdp, selector)
      await waitFor(
        cdp,
        `window.__eamosCopiedSample === ${JSON.stringify(`${BASE_URL}${path}`)}`,
        `copied ${path} sample link`,
      )
      const buttonText = await evaluateValue(
        cdp,
        `document.querySelector(${JSON.stringify(selector)})?.textContent?.trim()`,
      )
      assertDiscovery(buttonText === 'Link copied', `${path} has no visible copy confirmation`)
    }

    await navigate(
      cdp,
      `${BASE_URL}/report?fixture=rpe65-negative`,
      `document.querySelectorAll('[data-report-section-slot]').length >= 3`,
    )
    const reportRoute = await evaluateValue(cdp, `location.pathname + location.search`)
    assertDiscovery(reportRoute === '/report?fixture=rpe65-negative', 'copied report sample is not directly openable')

    await evaluateValue(cdp, `sessionStorage.removeItem('eamos.compare.v1')`)
    batchRequests.length = 0
    await navigate(
      cdp,
      `${BASE_URL}/compare?demo=1`,
      `document.body.innerText.includes('sample.vcf')
        && document.body.innerText.includes('Generate results')`,
    )
    await evaluateValue(cdp, `new Promise((resolve) => setTimeout(resolve, 500))`)
    const sample = await evaluateValue(
      cdp,
      `(() => {
        const stash = JSON.parse(sessionStorage.getItem('eamos.compare.v1') || 'null');
        const generate = Array.from(document.querySelectorAll('button'))
          .find((button) => button.textContent.includes('Generate results'));
        return {
          route: location.pathname + location.search,
          source: stash?.source ?? '',
          sources: stash?.sources?.length ?? 0,
          variants: stash?.variants?.length ?? 0,
          generateVisible: Boolean(generate && generate.getClientRects().length === 1),
          running: document.body.innerText.includes('Generating…'),
        };
      })()`,
    )
    assertDiscovery(sample.route === '/compare?demo=1', 'sample VCF permalink lost its route contract')
    assertDiscovery(sample.source === 'sample.vcf' && sample.sources === 1, 'fresh sample route did not hydrate one bundled source')
    assertDiscovery(sample.variants === 8, `fresh sample route hydrated ${sample.variants} variants instead of 8`)
    assertDiscovery(sample.generateVisible && !sample.running, 'sample route did not stop at the explicit Generate decision')
    assertDiscovery(batchRequests.length === 0, 'sample route started a Batch request without user action')

    if (runtimeErrors.length > 0) {
      throw new Error(`Browser runtime errors:\n${runtimeErrors.join('\n')}`)
    }
    process.stdout.write(
      'landing Pass 4: 2 safe share links, direct sample report, and 8-variant local Batch permalink verified; 0 automatic Batch requests\n',
    )
  } finally {
    cdp.close()
    chrome.cleanup()
  }
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
    await cdp.send('Accessibility.enable')
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: WIDTH,
      height: HEIGHT,
      deviceScaleFactor: 1,
      mobile: false,
    })
    await verifyHeroInTab(cdp)
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

async function verifyHero() {
  const response = await fetch(BASE_URL)
  if (!response.ok) throw new Error(`Eamos server returned HTTP ${response.status} at ${BASE_URL}`)
  const chrome = await spawnChrome()
  const tab = await openTab(chrome.port)
  const cdp = new CDP(tab.webSocketDebuggerUrl)
  const runtimeErrors = []
  cdp.on((event) => {
    if (event.method === 'Runtime.exceptionThrown') {
      runtimeErrors.push(event.params?.exceptionDetails?.exception?.description ?? 'Runtime exception')
    }
  })
  try {
    await cdp.ready
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Accessibility.enable')
    await verifyHeroInTab(cdp)
    if (runtimeErrors.length > 0) {
      throw new Error(`Browser runtime errors:\n${runtimeErrors.join('\n')}`)
    }
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

if (args['generate-social-card'] === 'true') {
  try {
    await generateSocialCard()
  } catch (error) {
    process.stderr.write(`landing social card: ${error.message}\n`)
    process.exitCode = 1
  }
} else if (args.check === 'true') {
  try {
    checkAssets()
  } catch (error) {
    process.stderr.write(`landing assets: ${error.message}\n`)
    process.exitCode = 1
  }
} else if (args['verify-pass4'] === 'true') {
  try {
    await verifyLandingPass3()
    await verifyLandingPass4()
  } catch (error) {
    process.stderr.write(`landing Pass 4: ${error.message}\n`)
    process.exitCode = 1
  }
} else if (args['verify-pass3'] === 'true') {
  try {
    await verifyLandingPass3()
  } catch (error) {
    process.stderr.write(`landing Pass 3: ${error.message}\n`)
    process.exitCode = 1
  }
} else if (args['verify-hero'] === 'true') {
  try {
    await verifyHero()
  } catch (error) {
    process.stderr.write(`landing hero: ${error.message}\n`)
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
