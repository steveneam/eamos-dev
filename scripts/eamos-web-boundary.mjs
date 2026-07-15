#!/usr/bin/env node
// eamos-web-boundary - structural boundary guard for the app/web Next.js surface.
//
// A node guard (no vitest harness in app/web) reusing the eamos-*.mjs idiom, run
// over GIT-TRACKED app/web files. It asserts three boundaries and signals via the
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
