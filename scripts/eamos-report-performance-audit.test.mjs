import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const AUDIT = join(ROOT, 'scripts', 'eamos-report-performance-audit.mjs')

async function withAuditServer(viewerStatus, run) {
  const server = createServer((request, response) => {
    const chunks = []
    request.on('data', (chunk) => chunks.push(chunk))
    request.on('end', () => {
      const body = chunks.length > 0 ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {}
      response.setHeader('content-type', 'application/json')
      if (request.url === '/api/v1/viewer') {
        response.statusCode = viewerStatus
        response.end(
          JSON.stringify(
            viewerStatus === 200
              ? { identity: { gene: body.gene }, provenance: { warnings: [] } }
              : { detail: { code: 'upstream_unavailable', message: 'viewer unavailable' } },
          ),
        )
        return
      }
      if (request.url === '/api/v1/lookup/sections') {
        const section = body.include?.[0] ?? 'publications'
        response.end(JSON.stringify({ sections: { [section]: { status: 'available', payload: {} } } }))
        return
      }
      response.end('{}')
    })
  })
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  try {
    const address = server.address()
    assert.ok(address && typeof address === 'object')
    await run(`http://127.0.0.1:${address.port}`)
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()))
    })
  }
}

function runAudit(base, extraArgs = []) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        AUDIT,
        `--base=${base}`,
        '--variant=RPE65:c.271C>T',
        '--section=publications',
        '--timeout=5000',
        ...extraArgs,
      ],
      { cwd: ROOT },
    )
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (chunk) => {
      stdout += chunk
    })
    child.stderr.on('data', (chunk) => {
      stderr += chunk
    })
    child.on('error', reject)
    child.on('close', (status) => resolve({ status, stdout, stderr }))
  })
}

test('--require-ok exits zero when every required endpoint is 2xx', async () => {
  await withAuditServer(200, async (base) => {
    const result = await runAudit(base, ['--require-ok'])
    assert.equal(result.status, 0, result.stderr || result.stdout)
    assert.match(result.stdout, /require_ok=true/)
    assert.doesNotMatch(result.stdout, /required endpoint failures:/)
  })
})

test('--require-ok turns a viewer 503 into an executable failure', async () => {
  await withAuditServer(503, async (base) => {
    const result = await runAudit(base, ['--require-ok'])
    assert.equal(result.status, 1, result.stderr || result.stdout)
    assert.match(result.stdout, /required endpoint failures:/)
    assert.match(result.stdout, /viewer status=503 error=.*upstream_unavailable/)
    assert.match(result.stdout, /viewer unavailable/)
  })
})
