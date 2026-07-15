#!/usr/bin/env node
// Scan text files for common UTF-8 mojibake sequences.
//
// This is intentionally read-only. It helps distinguish files that merely render
// badly in a Windows shell/tool path from files that already contain corrupted
// text containing common Latin-1-decoded UTF-8 marker bytes such as U+00C3,
// U+00C2, or U+00E2 followed by punctuation.
//
// Usage:
//   node scripts/eamos-encoding-scan.mjs
//   node scripts/eamos-encoding-scan.mjs agent_handoff docs
//   node scripts/eamos-encoding-scan.mjs --json --fail-on-hit
//   node scripts/eamos-encoding-scan.mjs agent_handoff/archive --include-archive

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { extname, join, resolve } from 'node:path'

const args = process.argv.slice(2)
const JSON_OUT = args.includes('--json')
const FAIL_ON_HIT = args.includes('--fail-on-hit')
const INCLUDE_ARCHIVE = args.includes('--include-archive')
const paths = args.filter((arg) => !arg.startsWith('--'))
const roots = paths.length ? paths : ['agent_handoff', 'docs', 'plans', 'scripts', 'app/backend']

const SKIP_DIRS = new Set([
  '.git',
  '.next',
  '.pytest_cache',
  '.ruff_cache',
  '.venv',
  '__pycache__',
  'dist',
  'node_modules',
])
const TEXT_EXTS = new Set([
  '.css',
  '.html',
  '.js',
  '.json',
  '.md',
  '.mjs',
  '.py',
  '.ps1',
  '.toml',
  '.ts',
  '.tsx',
  '.txt',
  '.yaml',
  '.yml',
])
const MAX_BYTES = 1_500_000
const MOJIBAKE_RE = new RegExp('(?:\\u00c3.|\\u00c2.|\\u00e2[^\\sA-Za-z0-9])', 'u')

function walk(path, out) {
  if (!existsSync(path)) return
  const stat = statSync(path)
  if (stat.isDirectory()) {
    const name = path.split(/[\\/]/).pop()
    if (SKIP_DIRS.has(name)) return
    if (!INCLUDE_ARCHIVE && name === 'archive') return
    for (const entry of readdirSync(path)) walk(join(path, entry), out)
    return
  }
  if (!stat.isFile() || stat.size > MAX_BYTES) return
  if (!TEXT_EXTS.has(extname(path).toLowerCase())) return
  out.push(path)
}

function scanFile(path) {
  const text = readFileSync(path, 'utf8')
  const findings = []
  const lines = text.split(/\r?\n/)
  lines.forEach((line, index) => {
    const match = MOJIBAKE_RE.exec(line)
    if (!match) return
    findings.push({
      line: index + 1,
      token: match[0],
      snippet: line.trim().slice(0, 180),
    })
  })
  return findings
}

const files = []
for (const root of roots) walk(resolve(root), files)

const results = []
for (const file of files.sort()) {
  const findings = scanFile(file)
  if (findings.length) results.push({ file, findings })
}

if (JSON_OUT) {
  process.stdout.write(JSON.stringify({ filesScanned: files.length, results }, null, 2) + '\n')
} else {
  process.stdout.write(`eamos-encoding-scan: scanned ${files.length} text files\n`)
  if (!results.length) {
    process.stdout.write('  clean: no common mojibake tokens found\n')
  } else {
    for (const result of results) {
      process.stdout.write(`  ${result.file}\n`)
      for (const finding of result.findings.slice(0, 5)) {
        process.stdout.write(
          `    L${finding.line}: ${finding.token}  ${finding.snippet}\n`,
        )
      }
      if (result.findings.length > 5) {
        process.stdout.write(`    ... ${result.findings.length - 5} more\n`)
      }
    }
  }
}

process.exit(results.length && FAIL_ON_HIT ? 1 : 0)
