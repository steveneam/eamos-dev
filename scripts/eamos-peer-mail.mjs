#!/usr/bin/env node

import {
  appendFileSync,
  closeSync,
  existsSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readFileSync,
  readdirSync,
  renameSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs'
import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const SCRIPT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const DEFAULT_REGISTRY = '.agent-mailboxes.json'
const RECEIPTS_FILE = 'receipts.json'
const LOCK_DIR = 'locks'
const SAFE_PLAN_MIN_CHARS = 24

export class PeerMailError extends Error {
  constructor(message, code = 'PEER_MAIL_ERROR', details = {}) {
    super(message)
    this.name = 'PeerMailError'
    this.code = code
    this.details = details
  }
}

function fail(message, code, details) {
  throw new PeerMailError(message, code, details)
}

function asPositiveNumber(value, name, fallback) {
  if (value === undefined || value === null || value === '') return fallback
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) fail(`${name} must be a positive number.`, 'INVALID_CONFIG')
  return parsed
}

function assertSlug(value, name) {
  if (typeof value !== 'string' || !/^[a-z0-9][a-z0-9_-]{0,63}$/i.test(value)) {
    fail(`${name} must be a short identifier containing only letters, numbers, underscores, or hyphens.`, 'INVALID_CONFIG')
  }
  return value
}

function assertLabel(value, name) {
  if (typeof value !== 'string' || value.trim().length < 1 || value.trim().length > 80 || /[\r\n]/.test(value)) {
    fail(`${name} must be a single non-empty line of at most 80 characters.`, 'INVALID_CONFIG')
  }
  return value.trim()
}

function pathInside(root, configuredPath, name) {
  if (typeof configuredPath !== 'string' || configuredPath.trim() === '' || isAbsolute(configuredPath)) {
    fail(`${name} must be a repository-relative path.`, 'INVALID_CONFIG')
  }
  const absolute = resolve(root, configuredPath)
  const rel = relative(root, absolute)
  if (rel === '' || rel === '..' || rel.startsWith(`..${sep}`) || isAbsolute(rel)) {
    fail(`${name} escapes the repository root.`, 'INVALID_CONFIG')
  }
  return { absolute, relative: rel.split(sep).join('/') }
}

function readJson(path, description) {
  let raw
  try {
    raw = readFileSync(path, 'utf8')
  } catch (error) {
    fail(`Cannot read ${description}: ${error.message}`, 'READ_ERROR', { path })
  }
  try {
    return JSON.parse(raw)
  } catch (error) {
    fail(`Cannot parse ${description}: ${error.message}`, 'INVALID_JSON', { path })
  }
}

export function runGit(root, args, { allowFailure = false } = {}) {
  const result = spawnSync('git', args, {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 8 * 1024 * 1024,
  })
  if (result.error) fail(`Could not run git ${args.join(' ')}: ${result.error.message}`, 'GIT_ERROR')
  if (result.status !== 0 && !allowFailure) {
    const message = (result.stderr || result.stdout || '').trim()
    fail(`git ${args.join(' ')} failed${message ? `: ${message}` : '.'}`, 'GIT_ERROR')
  }
  return result
}

export function findRepoRoot(explicitRoot = null, cwd = process.cwd()) {
  if (explicitRoot) return resolve(explicitRoot)
  const result = runGit(cwd, ['rev-parse', '--show-toplevel'], { allowFailure: true })
  if (result.status === 0 && result.stdout.trim()) return resolve(result.stdout.trim())
  return SCRIPT_ROOT
}

export function loadRegistry({ root = findRepoRoot(), registryPath = null } = {}) {
  const registryFile = registryPath
    ? resolve(root, registryPath)
    : resolve(root, DEFAULT_REGISTRY)
  const raw = readJson(registryFile, 'peer-mail registry')
  if (raw.version !== 1) fail('Peer-mail registry version must be 1.', 'INVALID_CONFIG')
  if (!raw.local || typeof raw.local !== 'object') fail('Peer-mail registry must define local.', 'INVALID_CONFIG')

  const local = {
    id: assertSlug(raw.local.id, 'local.id'),
    label: assertLabel(raw.local.label ?? raw.local.id, 'local.label'),
    signature: assertLabel(raw.local.signature ?? raw.local.label ?? raw.local.id, 'local.signature'),
  }
  const defaults = {
    lockTtlSeconds: asPositiveNumber(raw.defaults?.lockTtlSeconds, 'defaults.lockTtlSeconds', 1200),
    pollIntervalSeconds: asPositiveNumber(raw.defaults?.pollIntervalSeconds, 'defaults.pollIntervalSeconds', 5),
    maxMessageBytes: asPositiveNumber(raw.defaults?.maxMessageBytes, 'defaults.maxMessageBytes', 65536),
  }
  if (!Array.isArray(raw.mailboxes) || raw.mailboxes.length === 0) {
    fail('Peer-mail registry must define at least one mailbox.', 'INVALID_CONFIG')
  }

  const ids = new Set()
  const paths = new Set()
  const mailboxes = raw.mailboxes.map((entry, index) => {
    const base = `mailboxes[${index}]`
    const id = assertSlug(entry?.id, `${base}.id`)
    if (ids.has(id)) fail(`Duplicate mailbox id "${id}".`, 'INVALID_CONFIG')
    ids.add(id)
    if (!entry.peer || typeof entry.peer !== 'object') fail(`${base}.peer is required.`, 'INVALID_CONFIG')
    const peer = {
      id: assertSlug(entry.peer.id, `${base}.peer.id`),
      label: assertLabel(entry.peer.label ?? entry.peer.id, `${base}.peer.label`),
    }
    if (peer.id === local.id) fail(`${base}.peer.id must differ from local.id.`, 'INVALID_CONFIG')
    if (entry.owners?.outbound !== local.id) {
      fail(`${base}.owners.outbound must be the local owner "${local.id}".`, 'INVALID_CONFIG')
    }
    if (entry.owners?.inbound !== peer.id) {
      fail(`${base}.owners.inbound must be the peer owner "${peer.id}".`, 'INVALID_CONFIG')
    }

    const outboundPath = pathInside(root, entry.outbound?.path, `${base}.outbound.path`)
    const inboundPath = pathInside(root, entry.inbound?.path, `${base}.inbound.path`)
    for (const candidate of [outboundPath.relative, inboundPath.relative]) {
      if (paths.has(candidate)) fail(`Mailbox path "${candidate}" is registered more than once.`, 'INVALID_CONFIG')
      paths.add(candidate)
    }
    const headingLevel = Number(entry.outbound?.headingLevel ?? 2)
    if (!Number.isInteger(headingLevel) || headingLevel < 1 || headingLevel > 6) {
      fail(`${base}.outbound.headingLevel must be an integer from 1 through 6.`, 'INVALID_CONFIG')
    }
    const inboundLevels = entry.inbound?.headingLevels ?? [1]
    if (!Array.isArray(inboundLevels) || inboundLevels.length === 0 || inboundLevels.some((n) => !Number.isInteger(n) || n < 1 || n > 6)) {
      fail(`${base}.inbound.headingLevels must contain heading levels from 1 through 6.`, 'INVALID_CONFIG')
    }
    const appendMarker = entry.outbound?.appendMarker
    if (typeof appendMarker !== 'string' || appendMarker.trim().length < 4) {
      fail(`${base}.outbound.appendMarker must be a non-empty string.`, 'INVALID_CONFIG')
    }
    return {
      id,
      peer,
      owners: { outbound: local.id, inbound: peer.id },
      outbound: { ...outboundPath, headingLevel, appendMarker },
      inbound: { ...inboundPath, headingLevels: [...new Set(inboundLevels)] },
      allowDirtyInbound: entry.allowDirtyInbound === true,
    }
  })

  return { root: resolve(root), registryFile, local, defaults, mailboxes }
}

export function selectMailbox(registry, peerId) {
  if (!peerId) fail('A peer is required. Use --peer=<id>.', 'USAGE')
  const mailbox = registry.mailboxes.find((entry) => entry.id === peerId || entry.peer.id === peerId)
  if (!mailbox) fail(`Peer "${peerId}" is not registered.`, 'UNKNOWN_PEER')
  return mailbox
}

function splitZero(raw) {
  return raw.split('\0').filter(Boolean).map((value) => value.split('\\').join('/'))
}

export function gitChanges(root) {
  const staged = splitZero(runGit(root, ['diff', '--cached', '--name-only', '-z']).stdout)
  const tracked = splitZero(runGit(root, ['diff', '--name-only', '-z']).stdout)
  const untracked = splitZero(runGit(root, ['ls-files', '--others', '--exclude-standard', '-z']).stdout)
  return { staged, tracked, untracked, all: [...new Set([...staged, ...tracked, ...untracked])] }
}

export function stagingGuard(registry, changes = gitChanges(registry.root)) {
  const protectedPaths = new Set(
    registry.mailboxes
      .filter((mailbox) => mailbox.owners.inbound !== registry.local.id)
      .map((mailbox) => mailbox.inbound.relative),
  )
  const violations = changes.staged.filter((path) => protectedPaths.has(path))
  return { ok: violations.length === 0, violations, protectedPaths: [...protectedPaths].sort() }
}

export function hashText(text) {
  return createHash('sha256').update(text, 'utf8').digest('hex')
}

const SECRET_PATTERNS = [
  { name: 'private-key', regex: /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/g },
  { name: 'github-token', regex: /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b/g },
  { name: 'github-fine-grained-token', regex: /\bgithub_pat_[A-Za-z0-9_]{40,}\b/g },
  { name: 'aws-access-key', regex: /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/g },
  { name: 'slack-token', regex: /\bxox[baprs]-[A-Za-z0-9-]{20,}\b/g },
  { name: 'stripe-key', regex: /\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b/g },
  { name: 'jwt', regex: /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g },
  { name: 'credential-url', regex: /\b[a-z][a-z0-9+.-]*:\/\/[^\s/@:]+:[^\s/@]+@/gi },
  {
    name: 'assigned-secret',
    regex: /\b(?:password|passwd|api[_-]?key|access[_-]?token|secret[_-]?access[_-]?key|service[_-]?role)\s*[:=]\s*["']?[A-Za-z0-9/+_.-]{12,}/gi,
  },
]

export function secretFindings(text) {
  const findings = []
  for (const pattern of SECRET_PATTERNS) {
    pattern.regex.lastIndex = 0
    for (const match of text.matchAll(pattern.regex)) {
      const line = text.slice(0, match.index).split(/\r?\n/).length
      findings.push({ pattern: pattern.name, line })
    }
  }
  return findings
}

function parseHeadingStamp(line) {
  const dateMatch = /\b(\d{4})-(\d{2})-(\d{2})\b/.exec(line)
  if (!dateMatch) return null
  const timeMatch = /(?:^|[^\d])(?:~\s*)?(\d{2}):(\d{2})(?::(\d{2}))?\s*(?:UTC|Z)\b/i.exec(line)
  const date = `${dateMatch[1]}-${dateMatch[2]}-${dateMatch[3]}`
  if (!timeMatch) return { date, hasTime: false, time: null, epochMs: null }
  const hour = Number(timeMatch[1])
  const minute = Number(timeMatch[2])
  const second = Number(timeMatch[3] ?? 0)
  if (hour > 23 || minute > 59 || second > 59) return null
  const epochMs = Date.UTC(Number(dateMatch[1]), Number(dateMatch[2]) - 1, Number(dateMatch[3]), hour, minute, second)
  return { date, hasTime: true, time: `${timeMatch[1]}:${timeMatch[2]}:${String(second).padStart(2, '0')}`, epochMs }
}

export function headingStamps(text, levels) {
  const accepted = new Set(levels)
  const stamps = []
  text.split(/\r?\n/).forEach((line, index) => {
    const match = /^(#{1,6})\s+(.+)$/.exec(line)
    if (!match || !accepted.has(match[1].length)) return
    const stamp = parseHeadingStamp(match[2])
    if (stamp) stamps.push({ ...stamp, line: index + 1, heading: match[2].trim() })
  })
  return stamps
}

export function orderFindings(text, levels, { requireTimes = false } = {}) {
  const stamps = headingStamps(text, levels)
  const findings = []
  let previousDate = null
  let previousTimeForDate = null
  for (const stamp of stamps) {
    if (requireTimes && !stamp.hasTime) {
      findings.push({ line: stamp.line, reason: 'timestamp must include UTC time' })
      continue
    }
    if (previousDate && stamp.date < previousDate) {
      findings.push({ line: stamp.line, reason: `date ${stamp.date} precedes ${previousDate}` })
    } else if (previousDate === stamp.date && stamp.hasTime && previousTimeForDate && stamp.time < previousTimeForDate) {
      findings.push({ line: stamp.line, reason: `time ${stamp.time} precedes ${previousTimeForDate} on ${stamp.date}` })
    }
    if (!previousDate || stamp.date > previousDate) {
      previousDate = stamp.date
      previousTimeForDate = stamp.hasTime ? stamp.time : null
    } else if (stamp.date === previousDate && stamp.hasTime) {
      previousTimeForDate = stamp.time
    }
  }
  return { stamps, findings }
}

function readMailbox(path, label) {
  try {
    return readFileSync(path, 'utf8')
  } catch (error) {
    fail(`Cannot read ${label}: ${error.message}`, 'READ_ERROR', { path })
  }
}

export function inspectMailbox(mailbox, direction) {
  const descriptor = mailbox[direction]
  const text = readMailbox(descriptor.absolute, `${mailbox.id} ${direction} mailbox`)
  const levels = direction === 'outbound' ? [descriptor.headingLevel] : descriptor.headingLevels
  const order = orderFindings(text, levels, { requireTimes: direction === 'outbound' })
  const secrets = secretFindings(text)
  const markerMissing = direction === 'outbound' && !text.includes(descriptor.appendMarker)
  const stamps = order.stamps
  return {
    path: descriptor.relative,
    text,
    bytes: Buffer.byteLength(text, 'utf8'),
    sha256: hashText(text),
    latestHeading: stamps.length ? stamps.at(-1).heading.replace(/[\u0000-\u001f]/g, ' ').slice(0, 200) : null,
    orderFindings: order.findings,
    secretFindings: secrets,
    markerMissing,
    ok: order.findings.length === 0 && secrets.length === 0 && !markerMissing,
  }
}

function gitStatePath(root, ...parts) {
  const result = runGit(root, ['rev-parse', '--git-path', join('eamos-peer-mail', ...parts)])
  return resolve(root, result.stdout.trim())
}

function readLock(path, ttlSeconds, now = new Date()) {
  let metadata = null
  let createdAt = null
  try {
    metadata = readJson(path, 'peer-mail lock')
    createdAt = new Date(metadata.createdAt)
  } catch (error) {
    if (!(error instanceof PeerMailError)) throw error
  }
  const stat = statSync(path)
  const baseTime = createdAt && !Number.isNaN(createdAt.getTime()) ? createdAt.getTime() : stat.mtimeMs
  const ageSeconds = Math.max(0, (now.getTime() - baseTime) / 1000)
  return { path, metadata, ageSeconds, stale: ageSeconds > ttlSeconds }
}

export function mailboxLocks(registry, now = new Date()) {
  const directory = gitStatePath(registry.root, LOCK_DIR)
  if (!existsSync(directory)) return []
  return readdirSync(directory)
    .filter((name) => name.endsWith('.lock'))
    .map((name) => readLock(join(directory, name), registry.defaults.lockTtlSeconds, now))
}

function acquireMailboxLock(registry, mailbox, now = new Date()) {
  const directory = gitStatePath(registry.root, LOCK_DIR)
  mkdirSync(directory, { recursive: true, mode: 0o700 })
  const path = join(directory, `${mailbox.id}.lock`)
  let fd
  try {
    fd = openSync(path, 'wx', 0o600)
  } catch (error) {
    if (error.code !== 'EEXIST') fail(`Cannot create mailbox lock: ${error.message}`, 'LOCK_ERROR')
    const lock = readLock(path, registry.defaults.lockTtlSeconds, now)
    const state = lock.stale ? 'stale' : 'active'
    fail(`Mailbox "${mailbox.id}" has a ${state} lock (${Math.round(lock.ageSeconds)}s old). Inspect it before any manual removal.`, 'LOCKED', { stale: lock.stale, ageSeconds: lock.ageSeconds })
  }
  const metadata = {
    version: 1,
    mailbox: mailbox.id,
    owner: registry.local.id,
    pid: process.pid,
    createdAt: now.toISOString(),
  }
  writeFileSync(fd, `${JSON.stringify(metadata, null, 2)}\n`, 'utf8')
  fsyncSync(fd)
  closeSync(fd)
  return {
    path,
    release() {
      if (existsSync(path)) unlinkSync(path)
    },
  }
}

function ensureCleanMailboxInspection(inspection, label) {
  if (inspection.markerMissing) fail(`${label} is missing its configured append marker.`, 'MAILBOX_INVALID')
  if (inspection.orderFindings.length) {
    const first = inspection.orderFindings[0]
    fail(`${label} has out-of-order headings at line ${first.line}: ${first.reason}.`, 'MAILBOX_ORDER')
  }
  if (inspection.secretFindings.length) {
    const first = inspection.secretFindings[0]
    fail(`${label} contains a ${first.pattern} secret shape at line ${first.line}.`, 'SECRET_DETECTED')
  }
}

export function formatUtcMinute(date = new Date()) {
  const year = date.getUTCFullYear()
  const month = String(date.getUTCMonth() + 1).padStart(2, '0')
  const day = String(date.getUTCDate()).padStart(2, '0')
  const hour = String(date.getUTCHours()).padStart(2, '0')
  const minute = String(date.getUTCMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute} UTC`
}

export function sendMessage(registry, mailbox, { subject, body, now = new Date() }) {
  const guard = stagingGuard(registry)
  if (!guard.ok) fail(`Peer-owned inbound mailbox is staged: ${guard.violations.join(', ')}. Unstage it before sending.`, 'STAGING_GUARD')
  if (typeof subject !== 'string' || subject.trim().length < 3 || subject.trim().length > 160 || /[\r\n]/.test(subject)) {
    fail('Subject must be one line between 3 and 160 characters.', 'USAGE')
  }
  if (typeof body !== 'string' || body.trim().length === 0) fail('Message body must not be empty.', 'USAGE')
  if (Buffer.byteLength(body, 'utf8') > registry.defaults.maxMessageBytes) {
    fail(`Message exceeds the ${registry.defaults.maxMessageBytes}-byte limit.`, 'MESSAGE_TOO_LARGE')
  }
  const bodySecrets = secretFindings(`${subject}\n${body}`)
  if (bodySecrets.length) {
    fail(`Message contains a ${bodySecrets[0].pattern} secret shape. Use an owner-only secret channel instead.`, 'SECRET_DETECTED')
  }

  const lock = acquireMailboxLock(registry, mailbox, now)
  try {
    const before = inspectMailbox(mailbox, 'outbound')
    ensureCleanMailboxInspection(before, `${mailbox.id} outbound mailbox`)
    const lastTimed = headingStamps(before.text, [mailbox.outbound.headingLevel]).filter((stamp) => stamp.hasTime).at(-1)
    if (lastTimed && lastTimed.epochMs > now.getTime()) {
      fail('The newest outbound UTC stamp is in the future; refusing to append out of order.', 'MAILBOX_ORDER')
    }
    const hashes = '#'.repeat(mailbox.outbound.headingLevel)
    const normalizedBody = body.trim().replace(/\r\n/g, '\n')
    const message = `\n\n${hashes} ${formatUtcMinute(now)} · ${registry.local.label} → ${mailbox.peer.label} — ${subject.trim()}\n\n${normalizedBody}\n\n— ${registry.local.signature}\n`
    appendFileSync(mailbox.outbound.absolute, message, { encoding: 'utf8', mode: 0o600 })
    const fd = openSync(mailbox.outbound.absolute, 'r')
    fsyncSync(fd)
    closeSync(fd)
    const after = inspectMailbox(mailbox, 'outbound')
    ensureCleanMailboxInspection(after, `${mailbox.id} outbound mailbox`)
    return {
      ok: true,
      peer: mailbox.peer.id,
      path: mailbox.outbound.relative,
      stamp: formatUtcMinute(now),
      sha256Before: before.sha256,
      sha256After: after.sha256,
      bytesAdded: after.bytes - before.bytes,
    }
  } finally {
    lock.release()
  }
}

function readReceipts(registry) {
  const path = gitStatePath(registry.root, RECEIPTS_FILE)
  if (!existsSync(path)) return { path, data: { version: 1, peers: {} } }
  const data = readJson(path, 'peer-mail receipts')
  if (data.version !== 1 || typeof data.peers !== 'object' || data.peers === null) {
    fail('Peer-mail receipts file has an unsupported shape.', 'INVALID_STATE')
  }
  return { path, data }
}

function writeReceipts(path, data) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 })
  const temp = `${path}.${process.pid}.tmp`
  writeFileSync(temp, `${JSON.stringify(data, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 })
  renameSync(temp, path)
}

export function checkMailbox(registry, mailbox, { acknowledge = false, now = new Date() } = {}) {
  const guard = stagingGuard(registry)
  if (!guard.ok) fail(`Peer-owned inbound mailbox is staged: ${guard.violations.join(', ')}.`, 'STAGING_GUARD')
  const inspection = inspectMailbox(mailbox, 'inbound')
  ensureCleanMailboxInspection(inspection, `${mailbox.id} inbound mailbox`)
  const receipts = readReceipts(registry)
  const prior = receipts.data.peers[mailbox.id] ?? null
  const changed = prior?.sha256 !== inspection.sha256
  if (acknowledge) {
    receipts.data.peers[mailbox.id] = {
      sha256: inspection.sha256,
      acknowledgedAt: now.toISOString(),
      bytes: inspection.bytes,
    }
    writeReceipts(receipts.path, receipts.data)
  }
  return {
    ok: true,
    peer: mailbox.peer.id,
    path: mailbox.inbound.relative,
    changed,
    acknowledged: acknowledge,
    sha256: inspection.sha256,
    bytes: inspection.bytes,
    latestHeading: inspection.latestHeading,
    priorAcknowledgedAt: prior?.acknowledgedAt ?? null,
  }
}

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds))
}

export async function waitForMailbox(registry, mailbox, { timeoutSeconds = 60, intervalSeconds = null } = {}) {
  const timeout = asPositiveNumber(timeoutSeconds, 'timeout', 60)
  const interval = asPositiveNumber(intervalSeconds, 'interval', registry.defaults.pollIntervalSeconds)
  const initial = inspectMailbox(mailbox, 'inbound')
  ensureCleanMailboxInspection(initial, `${mailbox.id} inbound mailbox`)
  const started = Date.now()
  while ((Date.now() - started) / 1000 < timeout) {
    await delay(Math.min(interval * 1000, Math.max(10, timeout * 1000 - (Date.now() - started))))
    const current = inspectMailbox(mailbox, 'inbound')
    ensureCleanMailboxInspection(current, `${mailbox.id} inbound mailbox`)
    if (current.sha256 !== initial.sha256) {
      return {
        ok: true,
        changed: true,
        peer: mailbox.peer.id,
        path: mailbox.inbound.relative,
        waitedSeconds: Number(((Date.now() - started) / 1000).toFixed(3)),
        sha256: current.sha256,
        latestHeading: current.latestHeading,
      }
    }
  }
  return {
    ok: true,
    changed: false,
    timedOut: true,
    peer: mailbox.peer.id,
    path: mailbox.inbound.relative,
    waitedSeconds: Number(((Date.now() - started) / 1000).toFixed(3)),
    sha256: initial.sha256,
  }
}

export function statusReport(registry, { peerId = null, stagingOnly = false, now = new Date() } = {}) {
  const changes = gitChanges(registry.root)
  const staging = stagingGuard(registry, changes)
  const issues = staging.violations.map((path) => ({ code: 'STAGED_PEER_FILE', path }))
  if (stagingOnly) {
    return { ok: issues.length === 0, staging, issues, mailboxes: [] }
  }
  const selected = peerId ? [selectMailbox(registry, peerId)] : registry.mailboxes
  const mailboxes = selected.map((mailbox) => {
    const outbound = inspectMailbox(mailbox, 'outbound')
    const inbound = inspectMailbox(mailbox, 'inbound')
    if (!outbound.ok) issues.push({ code: 'INVALID_OUTBOUND', peer: mailbox.peer.id })
    if (!inbound.ok) issues.push({ code: 'INVALID_INBOUND', peer: mailbox.peer.id })
    return {
      id: mailbox.id,
      peer: mailbox.peer.id,
      outbound: {
        path: outbound.path,
        bytes: outbound.bytes,
        sha256: outbound.sha256,
        latestHeading: outbound.latestHeading,
        ok: outbound.ok,
        orderFindings: outbound.orderFindings,
        secretFindings: outbound.secretFindings,
        markerMissing: outbound.markerMissing,
      },
      inbound: {
        path: inbound.path,
        bytes: inbound.bytes,
        sha256: inbound.sha256,
        latestHeading: inbound.latestHeading,
        ok: inbound.ok,
        orderFindings: inbound.orderFindings,
        secretFindings: inbound.secretFindings,
      },
      inboundDirty: changes.tracked.includes(mailbox.inbound.relative),
      inboundStaged: changes.staged.includes(mailbox.inbound.relative),
    }
  })
  const locks = mailboxLocks(registry, now).map((lock) => ({
    mailbox: lock.metadata?.mailbox ?? null,
    owner: lock.metadata?.owner ?? null,
    ageSeconds: Number(lock.ageSeconds.toFixed(1)),
    stale: lock.stale,
  }))
  for (const lock of locks) issues.push({ code: lock.stale ? 'STALE_LOCK' : 'ACTIVE_LOCK', mailbox: lock.mailbox })
  return { ok: issues.length === 0, staging, issues, locks, mailboxes }
}

function sectionBody(markdown, heading) {
  const lines = markdown.split(/\r?\n/)
  const start = lines.findIndex((line) => line.trim() === `## ${heading}`)
  if (start < 0) return null
  const body = []
  for (let index = start + 1; index < lines.length; index += 1) {
    if (/^##\s+/.test(lines[index])) break
    body.push(lines[index])
  }
  return body.join('\n').trim()
}

function currentHandoffChecks(root) {
  const path = join(root, 'agent_handoff', 'CURRENT.md')
  const text = readMailbox(path, 'CURRENT.md')
  const issues = []
  const lockBody = sectionBody(text, 'Log Edit-Lock')
  if (!lockBody || !/^UNLOCKED\s+·/m.test(lockBody) || /^LOCKED:/m.test(lockBody)) {
    issues.push({ code: 'HANDOFF_LOCKED', message: 'CURRENT.md Log Edit-Lock is not released.' })
  }
  const sharedLocks = sectionBody(text, 'Shared File Locks')
  if (sharedLocks && /^-\s+\*\*/m.test(sharedLocks)) {
    issues.push({ code: 'SHARED_LOCK_ACTIVE', message: 'CURRENT.md still lists an active Shared File Lock.' })
  }
  const nextAction = sectionBody(text, 'Next Action')
  const planText = (nextAction ?? '').replace(/[`*_#>-]/g, ' ').replace(/\s+/g, ' ').trim()
  if (
    planText.length < SAFE_PLAN_MIN_CHARS ||
    !/^\s*-\s+\S/m.test(nextAction ?? '') ||
    /\b(?:TODO|TBD|unknown|decide later|ask what next)\b/i.test(planText)
  ) {
    issues.push({ code: 'NEXT_ACTION_MISSING', message: 'CURRENT.md needs a concrete bulleted Next Action.' })
  }
  return { path, issues, nextAction: nextAction ?? null }
}

function runHandoffLint(root) {
  const script = join(root, 'scripts', 'eamos-handoff-lint.mjs')
  const result = spawnSync(process.execPath, [script, '--strict'], {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 2 * 1024 * 1024,
  })
  return {
    ok: result.status === 0,
    status: result.status,
    summary: (result.stdout || result.stderr || '').trim().split(/\r?\n/).at(-1) ?? '',
  }
}

function upstreamState(root) {
  const upstream = runGit(root, ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}'], { allowFailure: true })
  if (upstream.status !== 0) return { ok: false, upstream: null, ahead: null, behind: null }
  const name = upstream.stdout.trim()
  const counts = runGit(root, ['rev-list', '--left-right', '--count', `HEAD...${name}`])
  const [ahead, behind] = counts.stdout.trim().split(/\s+/).map(Number)
  return { ok: ahead === 0 && behind === 0, upstream: name, ahead, behind }
}

export function clearSafeReport(registry) {
  const issues = []
  const status = statusReport(registry)
  for (const issue of status.issues) issues.push(issue)
  const handoff = currentHandoffChecks(registry.root)
  issues.push(...handoff.issues)
  const lint = runHandoffLint(registry.root)
  if (!lint.ok) issues.push({ code: 'HANDOFF_LINT', message: 'CURRENT.md failed strict handoff lint.' })

  const changes = gitChanges(registry.root)
  const allowedDirty = new Set(
    registry.mailboxes.filter((mailbox) => mailbox.allowDirtyInbound).map((mailbox) => mailbox.inbound.relative),
  )
  const uncommitted = changes.all.filter((path) => !allowedDirty.has(path))
  if (uncommitted.length) issues.push({ code: 'UNCOMMITTED', paths: uncommitted })
  const upstream = upstreamState(registry.root)
  if (!upstream.ok) issues.push({ code: 'UNPUSHED', upstream: upstream.upstream, ahead: upstream.ahead, behind: upstream.behind })

  return {
    ok: issues.length === 0,
    issues,
    evidence: {
      handoffUnlocked: handoff.issues.every((issue) => issue.code !== 'HANDOFF_LOCKED' && issue.code !== 'SHARED_LOCK_ACTIVE'),
      concreteNextAction: handoff.issues.every((issue) => issue.code !== 'NEXT_ACTION_MISSING'),
      handoffLint: lint,
      uncommitted,
      allowedDirtyInbound: changes.all.filter((path) => allowedDirty.has(path)),
      upstream,
      stagedPeerFiles: status.staging.violations,
      mailboxLocks: status.locks,
    },
  }
}

function parseArgs(argv) {
  const positionals = []
  const options = {}
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (!arg.startsWith('--')) {
      positionals.push(arg)
      continue
    }
    const equal = arg.indexOf('=')
    if (equal >= 0) {
      options[arg.slice(2, equal)] = arg.slice(equal + 1)
      continue
    }
    const key = arg.slice(2)
    const next = argv[index + 1]
    if (next !== undefined && !next.startsWith('--')) {
      options[key] = next
      index += 1
    } else {
      options[key] = true
    }
  }
  return { command: positionals[0] ?? 'help', positionals: positionals.slice(1), options }
}

function bodyFromOptions(options) {
  const bodyFile = options['body-file']
  if (!bodyFile) fail('send requires --body-file=<path> (use - for stdin).', 'USAGE')
  if (bodyFile === '-') return readFileSync(0, 'utf8')
  return readFileSync(resolve(String(bodyFile)), 'utf8')
}

function usage() {
  return `Eamos peer-mail coordination ratchet

Usage:
  node scripts/eamos-peer-mail.mjs status [--peer=<id>] [--staging-only] [--json]
  node scripts/eamos-peer-mail.mjs send --peer=<id> --subject=<text> --body-file=<path|-> [--json]
  node scripts/eamos-peer-mail.mjs check --peer=<id> [--ack] [--json]
  node scripts/eamos-peer-mail.mjs wait --peer=<id> [--timeout=<seconds>] [--interval=<seconds>] [--json]
  node scripts/eamos-peer-mail.mjs clear-safe [--json]

Common options: --root=<repo> --registry=<repo-relative-path>
`
}

function conciseText(command, result) {
  if (command === 'status') {
    if (!result.ok) return `peer-mail status: FAIL (${result.issues.map((issue) => issue.code).join(', ')})`
    if (result.mailboxes.length === 0) return 'peer-mail staging guard: PASS'
    const rows = result.mailboxes.map((mailbox) => {
      const dirty = mailbox.inboundDirty ? ', external update present' : ''
      return `${mailbox.peer}: outbound/inbound valid${dirty}`
    })
    return `peer-mail status: PASS\n${rows.map((row) => `  ${row}`).join('\n')}`
  }
  if (command === 'send') return `peer-mail send: appended ${result.bytesAdded} bytes to ${result.path} at ${result.stamp}`
  if (command === 'check') return `peer-mail check: ${result.changed ? 'new or unacknowledged content' : 'unchanged'} in ${result.path}${result.acknowledged ? ' (acknowledged)' : ''}${result.latestHeading ? `\n  latest: ${result.latestHeading}` : ''}`
  if (command === 'wait') return result.changed
    ? `peer-mail wait: update detected after ${result.waitedSeconds}s${result.latestHeading ? `\n  latest: ${result.latestHeading}` : ''}`
    : `peer-mail wait: no update within ${result.waitedSeconds}s`
  if (command === 'clear-safe') {
    if (!result.ok) return `clear-safe: REFUSED (${result.issues.map((issue) => issue.code).join(', ')})`
    return `clear-safe: PASS\n  handoff unlocked, next action concrete, strict lint clean, owned work committed, HEAD synced to ${result.evidence.upstream.upstream}`
  }
  return JSON.stringify(result, null, 2)
}

export async function main(argv = process.argv.slice(2)) {
  const parsed = parseArgs(argv)
  if (parsed.command === 'help' || parsed.options.help) {
    process.stdout.write(usage())
    return 0
  }
  const root = findRepoRoot(parsed.options.root ? String(parsed.options.root) : null)
  const registry = loadRegistry({ root, registryPath: parsed.options.registry ? String(parsed.options.registry) : null })
  let result
  if (parsed.command === 'status') {
    result = statusReport(registry, {
      peerId: parsed.options.peer ? String(parsed.options.peer) : null,
      stagingOnly: parsed.options['staging-only'] === true,
    })
  } else if (parsed.command === 'send') {
    const mailbox = selectMailbox(registry, parsed.options.peer)
    result = sendMessage(registry, mailbox, {
      subject: parsed.options.subject,
      body: bodyFromOptions(parsed.options),
    })
  } else if (parsed.command === 'check') {
    const mailbox = selectMailbox(registry, parsed.options.peer)
    result = checkMailbox(registry, mailbox, { acknowledge: parsed.options.ack === true })
  } else if (parsed.command === 'wait') {
    const mailbox = selectMailbox(registry, parsed.options.peer)
    result = await waitForMailbox(registry, mailbox, {
      timeoutSeconds: parsed.options.timeout ?? 60,
      intervalSeconds: parsed.options.interval ?? registry.defaults.pollIntervalSeconds,
    })
  } else if (parsed.command === 'clear-safe') {
    result = clearSafeReport(registry)
  } else {
    fail(`Unknown command "${parsed.command}".`, 'USAGE')
  }
  if (parsed.options.json === true) process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)
  else process.stdout.write(`${conciseText(parsed.command, result)}\n`)
  return result.ok === false || result.timedOut ? 1 : 0
}

const invokedPath = process.argv[1] ? resolve(process.argv[1]) : null
if (invokedPath === fileURLToPath(import.meta.url)) {
  main().then(
    (code) => process.exit(code),
    (error) => {
      if (error instanceof PeerMailError) {
        process.stderr.write(`peer-mail: ${error.message}\n`)
        process.exit(error.code === 'USAGE' ? 2 : 1)
      }
      process.stderr.write(`peer-mail: unexpected failure: ${error.stack ?? error.message}\n`)
      process.exit(1)
    },
  )
}
