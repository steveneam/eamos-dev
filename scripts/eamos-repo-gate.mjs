#!/usr/bin/env node

import { existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const BACKEND = join(ROOT, 'app', 'backend')
const WEB = join(ROOT, 'app', 'web')
const NODE = process.execPath
const NPM = process.platform === 'win32' ? 'npm.cmd' : 'npm'

function pythonCommand() {
  const candidates =
    process.platform === 'win32'
      ? [join(BACKEND, '.venv', 'Scripts', 'python.exe')]
      : [join(BACKEND, '.venv', 'bin', 'python')]
  return candidates.find(existsSync) ?? (process.platform === 'win32' ? 'python' : 'python3')
}

const PYTHON = pythonCommand()

const stages = {
  audit: [
    {
      label: 'web production dependency advisories (high or critical)',
      command: NPM,
      args: ['audit', '--omit=dev', '--audit-level=high'],
      cwd: WEB,
    },
    {
      label: 'backend dependency advisories',
      command: PYTHON,
      args: [
        '-m',
        'pip_audit',
        '--requirement',
        'requirements.txt',
        '--progress-spinner',
        'off',
      ],
      cwd: BACKEND,
    },
  ],
  guard: [
    {
      label: 'web structural boundary',
      command: NODE,
      args: [join(ROOT, 'scripts', 'eamos-web-boundary.mjs')],
      cwd: ROOT,
    },
    {
      label: 'backend boundary, structure, and contract canaries',
      command: PYTHON,
      args: [
        '-m',
        'pytest',
        'tests/test_boundary.py',
        'tests/test_structure_guard.py',
        'tests/test_frontend_contract.py',
        '-q',
      ],
      cwd: BACKEND,
    },
  ],
  lint: [
    { label: 'web ESLint', command: NPM, args: ['run', 'lint'], cwd: WEB },
    {
      label: 'backend Ruff',
      command: PYTHON,
      args: ['-m', 'ruff', 'check', 'app', 'tests'],
      cwd: BACKEND,
    },
    {
      label: 'backend Black',
      command: PYTHON,
      args: ['-m', 'black', '--check', 'app', 'tests'],
      cwd: BACKEND,
    },
  ],
  typecheck: [
    {
      label: 'web TypeScript',
      command: NPM,
      args: ['exec', '--', 'tsc', '--noEmit', '-p', 'tsconfig.json'],
      cwd: WEB,
    },
  ],
  test: [
    { label: 'web Vitest', command: NPM, args: ['run', 'test'], cwd: WEB },
    {
      label: 'backend pytest',
      command: PYTHON,
      args: ['-m', 'pytest', '-q'],
      cwd: BACKEND,
    },
  ],
  build: [
    { label: 'web production build', command: NPM, args: ['run', 'build'], cwd: WEB },
  ],
}

const requested = process.argv[2] ?? 'verify'
if (requested === '--help' || requested === '-h') {
  process.stdout.write(
    'Usage: node scripts/eamos-repo-gate.mjs [audit|guard|lint|typecheck|test|build|verify]\n',
  )
  process.exit(0)
}

const stageNames = requested === 'verify' ? ['guard', 'lint', 'typecheck', 'test', 'build'] : [requested]
if (stageNames.some((name) => !(name in stages))) {
  process.stderr.write(`Unknown gate "${requested}". Use --help for valid stages.\n`)
  process.exit(2)
}

const started = Date.now()
for (const stageName of stageNames) {
  for (const step of stages[stageName]) {
    process.stdout.write(`eamos:${stageName}: ${step.label}\n`)
    const result = spawnSync(step.command, step.args, {
      cwd: step.cwd,
      env: { ...process.env, LLM_PROVIDER: process.env.LLM_PROVIDER ?? 'mock' },
      stdio: 'inherit',
    })
    if (result.error) {
      process.stderr.write(`eamos:${stageName}: could not start ${step.label}: ${result.error.message}\n`)
      process.exit(1)
    }
    if (result.status !== 0) {
      process.stderr.write(`eamos:${stageName}: failed at ${step.label} (exit ${result.status})\n`)
      process.exit(result.status ?? 1)
    }
  }
}

const elapsedSeconds = ((Date.now() - started) / 1000).toFixed(1)
process.stdout.write(`eamos:${requested}: passed in ${elapsedSeconds}s\n`)
