#!/usr/bin/env node
// eamos install-hooks — point git at the tracked hooks dir (scripts/hooks).
//
// Wired as the root package.json `prepare` script (M-011) so `npm install`
// installs the pre-commit gate for every clone. Idempotent, and a safe no-op when
// git is unavailable or this is not a git checkout (it must never fail an
// `npm install`).
//
// Why core.hooksPath instead of copying into .git/hooks: the hook body is tracked
// at scripts/hooks/pre-commit, so pointing git at that directory means every clone
// and every linked worktree runs the SAME committed hook — there is no per-clone
// copy that silently goes stale (the copy-installed .git/hooks/pre-commit did).
// Setting core.hooksPath also makes git ignore .git/hooks entirely, so a legacy
// copy can no longer shadow the tracked hook; we additionally retire that legacy
// copy when it is demonstrably our own prior install.

import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, rmSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(HERE, '..')
// Relative path: git resolves it against each working tree's root at hook time,
// so it works for the main checkout and for linked worktrees alike.
const HOOKS_PATH = 'scripts/hooks'

function tryGit(args) {
  try {
    return { ok: true, out: execFileSync('git', args, { cwd: REPO_ROOT, encoding: 'utf8' }).trim() }
  } catch (err) {
    return { ok: false, error: err && err.message ? err.message : String(err) }
  }
}
function note(msg) {
  process.stdout.write(`install-hooks: ${msg}\n`)
}

// Safe no-op if git is missing or this is not a work tree — never fail npm install.
const inTree = tryGit(['rev-parse', '--is-inside-work-tree'])
if (!inTree.ok || inTree.out !== 'true') {
  note('not a git work tree (or git unavailable) — skipping hook install.')
  process.exit(0)
}

// Idempotent: only write core.hooksPath when it differs from the target.
const current = tryGit(['config', '--local', 'core.hooksPath'])
if (current.ok && current.out === HOOKS_PATH) {
  note(`core.hooksPath already ${HOOKS_PATH} — nothing to do.`)
} else {
  const set = tryGit(['config', 'core.hooksPath', HOOKS_PATH])
  if (!set.ok) {
    note(`could not set core.hooksPath (${set.error}) — skipping.`)
    process.exit(0)
  }
  note(`set core.hooksPath = ${HOOKS_PATH}`)
}

// Retire the legacy copy-installed .git/hooks/pre-commit so it cannot shadow the
// tracked hook if core.hooksPath is ever unset. Only remove OUR own prior copy
// (identified by the eamos signature line); never touch a foreign hook.
const commonDir = tryGit(['rev-parse', '--git-common-dir'])
if (commonDir.ok) {
  const legacy = resolve(REPO_ROOT, commonDir.out, 'hooks', 'pre-commit')
  if (existsSync(legacy)) {
    let body = ''
    try {
      body = readFileSync(legacy, 'utf8')
    } catch {
      body = ''
    }
    if (body.includes('eamos pre-commit')) {
      try {
        rmSync(legacy)
        note('removed superseded legacy .git/hooks/pre-commit (eamos copy).')
      } catch (err) {
        note(`could not remove legacy hook (${err.message}) — harmless; core.hooksPath overrides it.`)
      }
    } else {
      note('left a non-eamos .git/hooks/pre-commit in place (core.hooksPath overrides it).')
    }
  }
}

process.exit(0)
