#!/usr/bin/env node
// eamos-vault-mcp-preflight — executable ratchet for the Forj vault MCP wiring.
//
// The `obsidian-vault` MCP (Obsidian Local REST API, https://127.0.0.1:27124)
// is HTTPS on a SELF-SIGNED cert. If the agent host (Claude Code / Codex) does
// not inherit the right env at MCP startup, the server silently fails to
// connect and NO `mcp__obsidian-vault__*` tools register — the session looks
// like it has no vault access and the cause gets rediscovered from scratch
// (it did, 2026-07-08). A `curl -k` check HIDES this: `-k` skips cert
// validation, so curl passes while a Node host still fails on cert trust.
//
// This ratchet reproduces the MCP host's actual connection path — Node's TLS
// stack honoring NODE_EXTRA_CA_CERTS, WITHOUT disabling validation — so a green
// run proves the host will trust the cert, and a red run prints the exact fix.
// Run it after wiring the vault (especially on a fresh machine) instead of
// launching an agent host and guessing why the vault tools are missing.
//
// Checks (the 3 conditions from Wiki/portfolio/migration-runbook.md):
//   1. OBSIDIAN_API_KEY set in this process env (bearer auth).
//   2. NODE_EXTRA_CA_CERTS set AND the CA file exists (Node trusts the
//      self-signed cert). The CA regenerates per plugin install → re-export on
//      a new machine and re-point NODE_EXTRA_CA_CERTS.
//   3. Obsidian open + Local REST API plugin enabled — proven by an authed
//      HTTPS GET / returning { authenticated: true }.
//
// NOTE: this validates that THIS process (e.g. the Bash shell / a launched
// host) can reach the vault. The Claude Code / Codex *host* must be launched
// from an env that has both vars AND restarted so MCP re-initializes — a passing
// preflight in one shell does not retroactively wire an already-running host.
//
// Usage:
//   node scripts/eamos-vault-mcp-preflight.mjs            # human output
//   node scripts/eamos-vault-mcp-preflight.mjs --json     # machine output
//   node scripts/eamos-vault-mcp-preflight.mjs --url=https://127.0.0.1:27124/
//   node scripts/eamos-vault-mcp-preflight.mjs --timeout=5000
//
// Exit codes: 0 = vault reachable (PASS); 1 = not reachable (FAIL); 2 = usage.

import { existsSync } from 'node:fs'
import { get as httpsGet } from 'node:https'

const args = process.argv.slice(2)
const flag = (name, dflt) => {
  const hit = args.find((a) => a === `--${name}` || a.startsWith(`--${name}=`))
  if (!hit) return dflt
  const eq = hit.indexOf('=')
  return eq === -1 ? true : hit.slice(eq + 1)
}
if (flag('help', false)) {
  console.log('usage: node scripts/eamos-vault-mcp-preflight.mjs [--json] [--url=URL] [--timeout=MS]')
  process.exit(2)
}

const JSON_OUT = Boolean(flag('json', false))
const URL_ROOT = String(flag('url', 'https://127.0.0.1:27124/'))
const TIMEOUT = Number(flag('timeout', 5000))

const REMEDIATION = [
  '1. Open Obsidian with the Local REST API plugin enabled (localhost-only, same machine).',
  '2. Set OBSIDIAN_API_KEY + NODE_EXTRA_CA_CERTS (= ~/.claude/obsidian-rest-api-ca.pem) in the env',
  '   that LAUNCHES the agent host and is inherited by it (user-scope vars alone will NOT reach an',
  '   already-running host; the CA var is what makes Node trust the self-signed cert — curl -k hides this).',
  '3. Restart the agent host so MCP re-initializes. (The CA regenerates per plugin install → on a new',
  '   machine, re-export the CA and re-point NODE_EXTRA_CA_CERTS.)',
  'Canonical: vault Wiki/portfolio/migration-runbook.md · repo memory reference_vault_obsidian_mcp.',
]

const CERT_ERROR_CODES = new Set([
  'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
  'SELF_SIGNED_CERT_IN_CHAIN',
  'DEPTH_ZERO_SELF_SIGNED_CERT',
  'ERR_TLS_CERT_ALTNAME_INVALID',
  'CERT_HAS_EXPIRED',
])

function authedGet(url, apiKey) {
  return new Promise((resolve) => {
    const req = httpsGet(
      url,
      { headers: { Authorization: `Bearer ${apiKey}` }, timeout: TIMEOUT },
      (res) => {
        let body = ''
        res.on('data', (c) => (body += c))
        res.on('end', () => resolve({ ok: true, status: res.statusCode, body }))
      },
    )
    req.on('timeout', () => {
      req.destroy(Object.assign(new Error('request timed out'), { code: 'ETIMEDOUT' }))
    })
    req.on('error', (err) => resolve({ ok: false, code: err.code || 'ERR', message: err.message }))
  })
}

function fail(reason, hint) {
  const out = { pass: false, reason, hint, remediation: REMEDIATION }
  if (JSON_OUT) console.log(JSON.stringify(out, null, 2))
  else {
    console.log(`eamos-vault-mcp-preflight  ${URL_ROOT}`)
    console.log(`\n  [FAIL] ${reason}`)
    if (hint) console.log(`         ${hint}`)
    console.log('\n  Fix:')
    for (const line of REMEDIATION) console.log(`    ${line}`)
  }
  process.exit(1)
}

// ── 1. env presence ──────────────────────────────────────────────────────────
const apiKey = process.env.OBSIDIAN_API_KEY
if (!apiKey) fail('OBSIDIAN_API_KEY is not set in this process env.', 'The agent host cannot authenticate to the vault.')

const caPath = process.env.NODE_EXTRA_CA_CERTS
if (!caPath) {
  fail(
    'NODE_EXTRA_CA_CERTS is not set in this process env.',
    'Node cannot trust the self-signed cert; the MCP server will fail to connect.',
  )
}
if (!existsSync(caPath)) {
  fail(
    `NODE_EXTRA_CA_CERTS points to a missing file: ${caPath}`,
    'The CA regenerates per plugin install — re-export it and re-point the var.',
  )
}

// ── 2 + 3. real connection with cert validation ──────────────────────────────
const res = await authedGet(URL_ROOT, apiKey)

if (!res.ok) {
  if (res.code === 'ECONNREFUSED') {
    fail(
      `Connection refused at ${URL_ROOT}`,
      'Obsidian is not running, or the Local REST API plugin is disabled / on a different port.',
    )
  }
  if (CERT_ERROR_CODES.has(res.code)) {
    fail(
      `TLS certificate not trusted (${res.code}) at ${URL_ROOT}`,
      `NODE_EXTRA_CA_CERTS (${caPath}) does not match the running plugin's cert — re-export the CA (it regenerates per install).`,
    )
  }
  fail(`Could not reach the vault (${res.code}) at ${URL_ROOT}`, res.message)
}

let parsed
try {
  parsed = JSON.parse(res.body)
} catch {
  parsed = null
}

if (res.status === 401 || parsed?.authenticated === false) {
  fail('Reached the vault but authentication FAILED (401 / authenticated:false).', 'OBSIDIAN_API_KEY is wrong or stale for this Obsidian instance.')
}
if (res.status !== 200) {
  fail(`Unexpected HTTP ${res.status} from ${URL_ROOT}`, res.body?.slice(0, 200))
}

// ── PASS ─────────────────────────────────────────────────────────────────────
const service = parsed?.service ?? 'obsidian-local-rest-api'
const version = parsed?.versions?.self ?? parsed?.version ?? 'unknown'
const out = {
  pass: true,
  url: URL_ROOT,
  authenticated: parsed?.authenticated ?? true,
  service,
  version,
  ca: caPath,
}
if (JSON_OUT) console.log(JSON.stringify(out, null, 2))
else {
  console.log(`eamos-vault-mcp-preflight  ${URL_ROOT}`)
  console.log(`\n  [PASS] vault reachable + authenticated (cert validated via NODE_EXTRA_CA_CERTS)`)
  console.log(`         service ${service} v${version} · CA ${caPath}`)
  console.log(`\n  NOTE: this proves THIS process can reach the vault. The Claude Code / Codex host`)
  console.log(`        still needs to be LAUNCHED from an env with both vars + restarted so MCP`)
  console.log(`        re-initializes and the mcp__obsidian-vault__* tools register.`)
}
process.exit(0)
