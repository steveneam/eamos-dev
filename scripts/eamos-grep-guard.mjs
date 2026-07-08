#!/usr/bin/env node
// eamos-grep-guard - repo secret-shape + merge-conflict-marker guard.
//
// Scans GIT-TRACKED files only (git grep), so it sees exactly what a commit /
// CI checkout sees. Flags two committed-content hazards:
//   1. secret-shaped tokens  (Bearer <token>, sk-..., vck_...)
//   2. merge-conflict markers (<<<<<<<, =======, >>>>>>>)
//
// The forbidden patterns are ASSEMBLED FROM FRAGMENTS at runtime so the guard's
// own source never contains a literal secret prefix or a literal 7-char conflict
// marker - i.e. the guard passes its own scan (Swordfish leaked a guarded name
// because the guard's exit code never gated the commit; here the exit code is
// the contract).
//
// Line matching is CRLF-safe by construction: every pattern is anchored with ^
// (line start) or is a substring match, never whole-line equality, so a
// CRLF-terminated line (`=======\r`) still matches.
//
// Usage:
//   node scripts/eamos-grep-guard.mjs            # scan tracked files
//   node scripts/eamos-grep-guard.mjs --json     # machine output
//   node scripts/eamos-grep-guard.mjs --help
//
// Exit codes: 0 = clean, 1 = finding(s), 2 = usage / git error.

import { execFileSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(HERE, '..')

const argv = process.argv.slice(2)
if (argv.includes('--help') || argv.includes('-h')) {
  process.stdout.write(
    'Usage: node scripts/eamos-grep-guard.mjs [--json]\n' +
      'Scans git-tracked files for secret-shaped tokens and merge-conflict markers.\n' +
      'Exit: 0 clean, 1 finding(s), 2 error.\n',
  )
  process.exit(0)
}
const JSON_OUT = argv.includes('--json')

// Secret-shape patterns, assembled from fragments (POSIX ERE for `git grep -E`).
// The 24+ minimum length is what distinguishes a real key (sk- keys are 48 chars,
// vck_ tokens 24, JWT bearer tokens 100+, all high-entropy) from a dictionary
// placeholder (`Bearer service-role-secret` = 19, `vck_abcdefghijklmnop` = 16),
// so intentional test fixtures do not trip the guard.
const SK = 's' + 'k' + '-'
const VCK = 'v' + 'c' + 'k' + '_'
const BEARER = 'B' + 'earer'
const SECRET_PATTERNS = [
  `${BEARER}[ ][A-Za-z0-9_.=-]{24,}`,
  `${SK}[A-Za-z0-9]{24,}`,
  `${VCK}[A-Za-z0-9]{24,}`,
]

// Conflict markers, assembled so this file carries no literal 7-char marker.
// EXACTLY 7 chars followed by whitespace or end-of-line: this matches a real git
// marker (`<<<<<<< HEAD`, a lone `=======`, CRLF-terminated `=======\r` via the
// [[:space:]] class which includes CR) but NOT a decorative `====...` run of 8+,
// which is why the boundary group is required rather than a bare prefix match.
const BOUNDARY = '([[:space:]]|$)'
const CONFLICT_PATTERNS = [
  '^' + '<'.repeat(7) + BOUNDARY,
  '^' + '='.repeat(7) + BOUNDARY,
  '^' + '>'.repeat(7) + BOUNDARY,
]

// Run `git grep` for the given ERE patterns over tracked files. Returns the raw
// `path:line:content` hits. git grep exit: 0 = matches, 1 = none, >1 = error.
function gitGrep(patterns) {
  const args = ['grep', '-I', '-n', '-E']
  for (const p of patterns) args.push('-e', p)
  try {
    const out = execFileSync('git', args, {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      maxBuffer: 32 * 1024 * 1024,
    })
    return { hits: splitHits(out), ok: true }
  } catch (err) {
    if (err && err.status === 1) return { hits: [], ok: true } // no matches
    return { hits: [], ok: false, error: err && err.message ? err.message : String(err) }
  }
}

function splitHits(out) {
  return out
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const m = /^([^:]+):(\d+):(.*)$/.exec(line)
      if (!m) return { file: '?', line: 0, text: line.replace(/\r$/, '') }
      return { file: m[1], line: Number(m[2]), text: m[3].replace(/\r$/, '') }
    })
}

const secret = gitGrep(SECRET_PATTERNS)
const conflict = gitGrep(CONFLICT_PATTERNS)

if (!secret.ok || !conflict.ok) {
  const error = secret.error || conflict.error
  if (JSON_OUT) process.stdout.write(JSON.stringify({ status: 'error', error }, null, 2) + '\n')
  else process.stderr.write(`eamos-grep-guard: git error: ${error}\n`)
  process.exit(2)
}

const findings = [
  ...secret.hits.map((h) => ({ kind: 'secret', ...h })),
  ...conflict.hits.map((h) => ({ kind: 'conflict-marker', ...h })),
]

if (JSON_OUT) {
  process.stdout.write(
    JSON.stringify({ status: findings.length ? 'failed' : 'ok', findings }, null, 2) + '\n',
  )
} else if (findings.length === 0) {
  process.stdout.write('eamos-grep-guard: clean - no secret-shaped tokens or conflict markers in tracked files.\n')
} else {
  process.stderr.write(`eamos-grep-guard: ${findings.length} finding(s) in tracked files:\n`)
  for (const f of findings) {
    const preview = f.text.length > 80 ? f.text.slice(0, 80) + '...' : f.text
    process.stderr.write(`  [${f.kind}] ${f.file}:${f.line}: ${preview}\n`)
  }
}

process.exit(findings.length ? 1 : 0)
