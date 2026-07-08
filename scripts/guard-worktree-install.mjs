#!/usr/bin/env node
// guard-worktree-install - preinstall ratchet: never `npm install` inside a worktree.
//
// npm v7+ DELETES a linked (symlink/junction) node_modules and replaces it with a
// real per-lane folder, forking the lane's dependency tree and breaking the shared
// install model. Installs must run in the MAIN checkout only; the symlink/junction
// (see scripts/eamos-worktree-setup.ps1) makes them visible to every lane.
//
// Detection is by .git shape, walking up from the cwd to the nearest .git:
//   - .git is a regular FILE   -> a git worktree            -> ABORT (exit 1)
//   - .git is a directory      -> a normal full clone       -> allow (exit 0)
//   - no .git found            -> git archive / shallow tar -> allow (exit 0)
//
// The fail-open-unless-.git-is-a-FILE rule is load-bearing: CI, Vercel, and Render
// all install from full clones (.git is a directory), so this guard NEVER blocks a
// production/CI install - it only fires for a human `npm install` in a lane.

import { existsSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'

function findDotGit(startDir) {
  let dir = startDir
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const candidate = join(dir, '.git')
    if (existsSync(candidate)) return candidate
    const parent = dirname(dir)
    if (parent === dir) return null // reached filesystem root
    dir = parent
  }
}

const dotGit = findDotGit(process.cwd())

if (!dotGit) {
  process.exit(0) // no .git (archive/shallow tarball) -> fail open
}

let isFile = false
try {
  isFile = statSync(dotGit).isFile()
} catch {
  process.exit(0) // unreadable -> fail open, never block an install on a stat error
}

if (!isFile) {
  process.exit(0) // .git is a directory (normal clone) -> allow install
}

// .git is a regular file -> this is a git worktree. Abort the install.
process.stderr.write(
  [
    '',
    'guard-worktree-install: refusing `npm install` inside a git worktree.',
    `  worktree marker: ${dotGit}`,
    '',
    '  npm would delete the linked node_modules and fork this lane\'s dependency tree.',
    '  Run installs in the MAIN checkout only; the symlink/junction created by',
    '  scripts/eamos-worktree-setup.ps1 makes them visible to every lane instantly.',
    '',
  ].join('\n') + '\n',
)
process.exit(1)
