#!/usr/bin/env node

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const BACKEND = join(ROOT, 'app', 'backend')
const VENV_PYTHON =
  process.platform === 'win32'
    ? join(BACKEND, '.venv', 'Scripts', 'python.exe')
    : join(BACKEND, '.venv', 'bin', 'python')
const PYTHON = existsSync(VENV_PYTHON)
  ? VENV_PYTHON
  : process.platform === 'win32'
    ? 'python'
    : 'python3'

const child = spawn(
  PYTHON,
  [
    '-m',
    'uvicorn',
    'app.main:create_app',
    '--factory',
    '--host',
    '127.0.0.1',
    '--port',
    '8532',
    '--reload',
    ...process.argv.slice(2),
  ],
  {
    cwd: BACKEND,
    env: { ...process.env, HOST: '127.0.0.1', PORT: '8532' },
    stdio: 'inherit',
  },
)

child.once('error', (error) => {
  process.stderr.write(`eamos:dev:backend: could not start ${PYTHON}: ${error.message}\n`)
  process.exitCode = 1
})

child.once('exit', (code) => {
  process.exitCode = code ?? 1
})
