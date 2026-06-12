#!/usr/bin/env node
// eamos-handoff-lint — proprietary anti-bloat preflight for the agent handoff.
//
// agent_handoff/CURRENT.md is "live state only" (README Hard Rule 9), but the
// rules that keep it small — replace-never-stack, single-mutex lock, prune
// DONE/released entries — are only enforced by discipline, so over weeks it
// ballooned to 2309 lines with two ~28k-char heartbeat lines. This script
// enforces those rules MECHANICALLY by failing/warning on the exact bloat
// signatures, so both agents (and an optional pre-commit hook) catch drift at
// the moment it happens instead of at the next manual trim.
//
// Checks:
//   • total line count                         (WARN >400, FAIL >500)
//   • any single physical line too long        (FAIL >2000 chars — the
//                                                giant-heartbeat anti-pattern)
//   • Active Status bullet too long            (WARN >1500 chars — a heartbeat
//                                                should be a pointer, not a dump)
//   • Log Edit-Lock status-line count          (WARN >1, FAIL >4 — it is a
//                                                single mutex; history is git)
//   • Shared File Lock entries older than 7d   (WARN — a released/old lock is
//                                                history; prune to PROGRESS.md)
//   • Cross-Agent Requests: DONE older than 7d / OPEN older than 14d  (WARN)
//
// Usage:
//   node scripts/eamos-handoff-lint.mjs                         # lint CURRENT.md
//   node scripts/eamos-handoff-lint.mjs --file=PATH             # lint another file
//   node scripts/eamos-handoff-lint.mjs --today=2026-06-12      # pin clock (tests)
//   node scripts/eamos-handoff-lint.mjs --strict                # warnings -> failure
//   node scripts/eamos-handoff-lint.mjs --json                  # machine output
//
// Exit codes: 0 = clean (or warnings-only without --strict); 1 = failures
// present (or any warning under --strict); 2 = usage/read error.

import { readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

// ─────────────────────────────────────────────────────────────────────────────
// Thresholds (single home — tune here)

const WARN_TOTAL_LINES = 400
const FAIL_TOTAL_LINES = 500
const FAIL_LINE_CHARS = 2000
const WARN_HEARTBEAT_CHARS = 1500
const WARN_LOCK_STATUS_LINES = 1
const FAIL_LOCK_STATUS_LINES = 4
const STALE_LOCK_DAYS = 7
const STALE_DONE_DAYS = 7
const STALE_OPEN_DAYS = 14

// ─────────────────────────────────────────────────────────────────────────────
// CLI args

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v = 'true'] = a.replace(/^--/, '').split('=')
    return [k, v]
  }),
)
const HERE = dirname(fileURLToPath(import.meta.url))
const FILE = resolve(args.file ?? join(HERE, '..', 'agent_handoff', 'CURRENT.md'))
const STRICT = args.strict === 'true'
const JSON_OUT = args.json === 'true'

function parseToday(s) {
  if (!s || s === 'true') return startOfUtcDay(new Date())
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
  if (!m) fail(`--today must be YYYY-MM-DD (got "${s}")`)
  return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]))
}
const TODAY = parseToday(args.today)

// ─────────────────────────────────────────────────────────────────────────────
// helpers

function fail(msg) {
  process.stderr.write(`eamos-handoff-lint: ${msg}\n`)
  process.exit(2)
}
function startOfUtcDay(d) {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()))
}
const DATE_RE = /(\d{4})-(\d{2})-(\d{2})/g
function datesIn(text) {
  const out = []
  for (const m of text.matchAll(DATE_RE)) {
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]))
    if (!Number.isNaN(d.getTime()) && d.getUTCMonth() === +m[2] - 1) out.push(d)
  }
  return out
}
function newestDate(text) {
  const ds = datesIn(text)
  return ds.length ? new Date(Math.max(...ds.map((d) => d.getTime()))) : null
}
function ageDays(d) {
  return Math.floor((TODAY.getTime() - d.getTime()) / 86_400_000)
}
function iso(d) {
  return d.toISOString().slice(0, 10)
}

// Split `lines` into `## ` sections. Returns [{title, start, lines}].
function sections(lines) {
  const out = []
  let cur = null
  lines.forEach((line, i) => {
    if (line.startsWith('## ')) {
      cur = { title: line.trim(), start: i + 1, lines: [] }
      out.push(cur)
    } else if (cur) {
      cur.lines.push(line)
    }
  })
  return out
}
function findSection(secs, prefix) {
  return secs.find((s) => s.title.startsWith(prefix)) ?? null
}
// Group a section's body lines into bullet-led entries.
function entries(sectionLines, bulletRe) {
  const out = []
  let cur = null
  for (const line of sectionLines) {
    if (bulletRe.test(line)) {
      cur = [line]
      out.push(cur)
    } else if (cur) {
      cur.push(line)
    }
  }
  return out
}

// ─────────────────────────────────────────────────────────────────────────────
// lint

let text
try {
  text = readFileSync(FILE, 'utf8')
} catch (e) {
  fail(`cannot read ${FILE}: ${e.message}`)
}
const lines = text.split('\n')
const lineCount = lines[lines.length - 1] === '' ? lines.length - 1 : lines.length
const secs = sections(lines)
const findings = []
const add = (level, msg) => findings.push({ level, msg })

// 1) total size
if (lineCount > FAIL_TOTAL_LINES)
  add('FAIL', `${lineCount} lines (> ${FAIL_TOTAL_LINES}) — archive >1wk logs and refresh stale state sections.`)
else if (lineCount > WARN_TOTAL_LINES)
  add('WARN', `${lineCount} lines (> ${WARN_TOTAL_LINES}) — trim soon; archive >1wk logs.`)

// 2) any giant physical line
lines.forEach((line, i) => {
  if (line.length > FAIL_LINE_CHARS)
    add('FAIL', `line ${i + 1} is ${line.length} chars (> ${FAIL_LINE_CHARS}) — collapse it; state is a pointer, not a narrative dump: "${line.slice(0, 50).trim()}…"`)
})

// 3) Active Status heartbeat bullets
const as = findSection(secs, '## Active Status')
if (as) {
  for (const line of as.lines) {
    if (line.startsWith('- **') && line.length > WARN_HEARTBEAT_CHARS)
      add('WARN', `Active Status bullet is ${line.length} chars (> ${WARN_HEARTBEAT_CHARS}) — keep it one short state-only line; narrative -> next-session doc, handoffs -> Cross-Agent Requests.`)
  }
}

// 4) Log Edit-Lock single-mutex
const lock = findSection(secs, '## Log Edit-Lock')
if (lock) {
  const status = lock.lines.filter((l) => /^(LOCKED|UNLOCKED)\b/.test(l))
  if (status.length > FAIL_LOCK_STATUS_LINES)
    add('FAIL', `Log Edit-Lock has ${status.length} status lines (> ${FAIL_LOCK_STATUS_LINES}) — it is a single mutex; keep only the current line (lock history lives in git).`)
  else if (status.length > WARN_LOCK_STATUS_LINES)
    add('WARN', `Log Edit-Lock has ${status.length} status lines — replace, never append; keep only the current line.`)
}

// 5) Shared File Locks staleness
const sfl = findSection(secs, '## Shared File Locks')
if (sfl) {
  for (const e of entries(sfl.lines, /^- \*\*/)) {
    const d = newestDate(e.join('\n'))
    if (d && ageDays(d) > STALE_LOCK_DAYS)
      add('WARN', `Shared File Lock entry from ${iso(d)} (${ageDays(d)}d old) — a released/old lock is history, not state; prune to PROGRESS.md: "${e[0].replace(/^- /, '').slice(0, 50).trim()}…"`)
  }
}

// 6) Cross-Agent Requests staleness
const car = findSection(secs, '## Cross-Agent Requests')
if (car) {
  for (const e of entries(car.lines, /^- \[/)) {
    const status = (/^- \[([A-Z-]+)\]/.exec(e[0])?.[1]) ?? ''
    const terminal = /DONE|CLOSED/.test(status)
    const limit = terminal ? STALE_DONE_DAYS : STALE_OPEN_DAYS
    const d = newestDate(e.join('\n'))
    if (d && ageDays(d) > limit) {
      const how = terminal ? 'prune to PROGRESS.md' : 'resolve or archive — a weeks-old OPEN is rarely still live'
      add('WARN', `Cross-Agent Request [${status}] from ${iso(d)} (${ageDays(d)}d > ${limit}d) — ${how}: "${e[0].replace(/^- \[[A-Z-]+\]\s*/, '').slice(0, 45).trim()}…"`)
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// report

const failures = findings.filter((f) => f.level === 'FAIL').length
const warnings = findings.filter((f) => f.level === 'WARN').length
const ok = failures === 0 && (!STRICT || warnings === 0)

if (JSON_OUT) {
  process.stdout.write(
    JSON.stringify({ file: FILE, today: iso(TODAY), lineCount, failures, warnings, strict: STRICT, ok, findings }, null, 2) + '\n',
  )
} else {
  process.stdout.write(`eamos-handoff-lint  ${FILE}\n`)
  process.stdout.write(`  ${lineCount} lines · today ${iso(TODAY)}${STRICT ? ' · strict' : ''}\n\n`)
  if (findings.length === 0) {
    process.stdout.write('  [ ok ] clean — handoff is lean and current.\n')
  } else {
    for (const f of findings) process.stdout.write(`  [${f.level === 'FAIL' ? 'FAIL' : 'warn'}] ${f.msg}\n`)
  }
  process.stdout.write(`\n  ${failures} failure(s), ${warnings} warning(s) — ${ok ? 'PASS' : 'FAIL'}\n`)
}

process.exit(ok ? 0 : 1)
