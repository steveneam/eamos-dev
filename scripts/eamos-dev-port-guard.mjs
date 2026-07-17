#!/usr/bin/env node

import { readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const FRONTEND_PORT = 3532
const BACKEND_PORT = 8532
const failures = []

function read(relativePath) {
  return readFileSync(join(ROOT, relativePath), 'utf8')
}

function requireText(relativePath, expected) {
  if (!read(relativePath).includes(expected)) {
    failures.push(`${relativePath} must contain ${JSON.stringify(expected)}`)
  }
}

const rootPackage = JSON.parse(read('package.json'))
const webPackage = JSON.parse(read('app/web/package.json'))

if (webPackage.scripts?.dev !== `next dev -p ${FRONTEND_PORT}`) {
  failures.push(`app/web/package.json dev script must pin frontend port ${FRONTEND_PORT}`)
}
if (rootPackage.scripts?.['dev:backend'] !== 'node scripts/eamos-repo-gate.mjs dev:backend') {
  failures.push('package.json dev:backend script must route through the repository gate')
}

for (const relativePath of [
  'app/web/next.config.mjs',
  'app/web/app/api/v1/search/route.ts',
  'app/web/app/api/v1/lookup/route.ts',
  'app/web/app/api/v1/library/views/[...query_id]/route.ts',
]) {
  requireText(relativePath, `http://localhost:${BACKEND_PORT}`)
}

requireText('scripts/eamos-backend-dev.mjs', `'${BACKEND_PORT}'`)
requireText('scripts/eamos-backend-dev.mjs', `PORT: '${BACKEND_PORT}'`)
requireText(
  'scripts/eamos-report-preflight.mjs',
  `http://localhost:${FRONTEND_PORT}/report?fixture=rpe65-negative`,
)
requireText('scripts/eamos-capture-landing-features.mjs', `http://localhost:${FRONTEND_PORT}`)

if (failures.length > 0) {
  process.stderr.write(`eamos:dev-ports: failed\n- ${failures.join('\n- ')}\n`)
  process.exit(1)
}

process.stdout.write(
  `eamos:dev-ports: frontend ${FRONTEND_PORT} and backend ${BACKEND_PORT} are pinned\n`,
)
