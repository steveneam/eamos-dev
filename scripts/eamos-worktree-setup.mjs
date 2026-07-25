#!/usr/bin/env node
// eamos-worktree-setup - prepare a lane worktree on Linux/macOS.
//
// Why this exists: `guard-worktree-install.mjs` blocks `npm install` inside a
// worktree and points at `eamos-worktree-setup.ps1` for the linking step - but
// that script is PowerShell, from the Windows era, with no POSIX equivalent. On
// this box a fresh worktree therefore had NO deps at all and no documented way
// to get them, which would block any parallel window.
//
// The model is thalon's, and it is measured rather than assumed. Installs live
// in the MAIN checkout; a lane LINKS to them. Verified on syd4 2026-07-25 in a
// probe worktree, all through the links:
//   pytest -n 2 (resolves the LANE's app package, not main's)  ... pass
//   eslint      (thalon's canary - the thing that half-works silently) pass
//   vitest      (37 files / 258 tests)                          ... pass
//   eamos-web-boundary.mjs                                      ... pass
// Linking costs ~0 bytes and no install time per lane; a fresh venv plus
// node_modules would cost ~1.6 GB and several minutes each.
//
// Usage (from the MAIN checkout, after founder approval of the partition):
//   node scripts/eamos-worktree-setup.mjs <lane-name> [branch]
// Creates .claude/worktrees/<lane-name> on branch agent/live/<lane-name>
// (override with the second argument), links deps, and verifies them.
//
// It refuses rather than guesses: no main-checkout deps, an existing worktree,
// or a failed post-link verification all stop with a non-zero exit.

import { execFileSync } from 'node:child_process'
import { existsSync, lstatSync, symlinkSync, mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..')

// Each entry is linked from the main checkout into the lane. Both are gitignored,
// so a fresh worktree never carries them.
const LINKS = [
  { rel: 'app/backend/.venv', label: 'backend venv' },
  { rel: 'app/web/node_modules', label: 'web node_modules' },
]

function die(message) {
  console.error(`eamos-worktree-setup: ${message}`)
  process.exit(1)
}

function git(args, cwd = REPO) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' }).trim()
}

const lane = process.argv[2]
if (!lane) die('usage: eamos-worktree-setup.mjs <lane-name> [branch]')
if (!/^[a-z0-9][a-z0-9-]*$/.test(lane)) die(`lane name must be kebab-case: ${lane}`)
const branch = process.argv[3] ?? `agent/live/${lane}`

// A worktree inside a worktree is one of the two mishaps thalon logged; refuse it.
if (lstatSync(join(REPO, '.git')).isFile()) {
  die('run this from the MAIN checkout, not a worktree')
}

for (const { rel, label } of LINKS) {
  if (!existsSync(join(REPO, rel))) {
    die(`main checkout is missing ${rel} (${label}) - install it there first, never in a lane`)
  }
}

const worktree = join(REPO, '.claude/worktrees', lane)
if (existsSync(worktree)) die(`${worktree} already exists - refusing to clobber a lane`)

// Absolute paths throughout: cwd persistence across shell calls is exactly what
// produced thalon's nested-worktree and stray-branch incidents.
mkdirSync(dirname(worktree), { recursive: true })
const exists = git(['branch', '--list', branch])
git(exists
  ? ['worktree', 'add', worktree, branch]
  : ['worktree', 'add', worktree, '-b', branch, 'main'])
console.log(`worktree ${worktree}\nbranch   ${branch}${exists ? ' (existing)' : ' (new, from main)'}`)

for (const { rel, label } of LINKS) {
  symlinkSync(join(REPO, rel), join(worktree, rel))
  console.log(`linked   ${rel}  (${label})`)
}

// Verify the links actually resolve rather than trusting that they exist. The
// backend check asserts the LANE's package wins, because a link that silently
// resolved to the main checkout would make a lane test green against the wrong
// code - the worst available failure mode.
const probe = 'import app.capabilities.composition as c; print(c.__file__)'
let resolved
try {
  resolved = execFileSync(
    join(worktree, 'app/backend/.venv/bin/python'),
    ['-c', `import sys; sys.path.insert(0, "app/backend"); ${probe}`],
    { cwd: worktree, encoding: 'utf8' },
  ).trim()
} catch (err) {
  die(`backend venv link is broken: ${err.message}`)
}
if (!resolved.startsWith(worktree)) {
  die(`backend imports resolved to ${resolved} instead of this lane - refusing to hand over a lane that tests the wrong tree`)
}
console.log(`verified backend imports resolve to the lane`)

// thalon's canary: node resolution walks up to the main checkout, so vitest can
// pass while eslint (workspace-nested deps) fails. Check the harder one.
try {
  execFileSync('npm', ['--prefix', 'app/web', 'run', 'lint'], { cwd: worktree, stdio: 'ignore' })
  console.log('verified web .bin-through-link (eslint)')
} catch {
  die('eslint failed through the node_modules link - the .bin path is broken; fix before handing over the lane')
}

console.log(`
lane ready. Notes that are not optional:
  - cap tests at -n 2, never -n auto (4 lanes x auto = 24 procs on 6 vCPU)
  - no dev server or headless browser in a lane (Turbopack fatals on
    out-of-root symlinks); visual checks run on the lead's checkout after rebase
  - never 'npm install' here - guard-worktree-install.mjs will stop you
  - kill processes by PID from 'pgrep -af', never 'pkill -f'`)
