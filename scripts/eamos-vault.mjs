#!/usr/bin/env node
// eamos-vault — read-only CLI access to the Forj vault (Obsidian Local REST API).
//
// The `obsidian-vault` MCP tools only register if the agent host is launched
// with the right env; when they don't (common), a session has NO vault access
// and the cause gets rediscovered. But the vault REST API is reachable from any
// process that has OBSIDIAN_API_KEY + NODE_EXTRA_CA_CERTS (verify with
// scripts/eamos-vault-mcp-preflight.mjs). This CLI uses that path directly, so
// an agent can read/list/search the vault WITHOUT the MCP tools wired — no host
// relaunch, no human relay.
//
// READ-ONLY by design (mirrors the .claude/settings.local.json allowlist):
// info / list / read / search only. No write/patch/delete/move/execute/open.
//
// Usage:
//   node scripts/eamos-vault.mjs info
//   node scripts/eamos-vault.mjs list [DIR]            # list a folder (root if omitted)
//   node scripts/eamos-vault.mjs read <PATH>           # print a note's markdown
//   node scripts/eamos-vault.mjs search <QUERY>        # simple text search
//   ...any command + --json for machine output
//
// Exit: 0 ok · 1 request/usage error · 2 not reachable (run the preflight).

import { request as httpsRequest } from 'node:https'

const BASE = process.env.EAMOS_VAULT_URL || 'https://127.0.0.1:27124'
const KEY = process.env.OBSIDIAN_API_KEY
const TIMEOUT = 8000

const argv = process.argv.slice(2)
const JSON_OUT = argv.includes('--json')
const positional = argv.filter((a) => !a.startsWith('--'))
const [cmd, ...rest] = positional

if (!KEY) {
  console.error('OBSIDIAN_API_KEY not set. Run: node scripts/eamos-vault-mcp-preflight.mjs')
  process.exit(2)
}

function req(method, path, { query, accept } = {}) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BASE)
    if (query) for (const [k, v] of Object.entries(query)) url.searchParams.set(k, String(v))
    const r = httpsRequest(
      url,
      { method, headers: { Authorization: `Bearer ${KEY}`, Accept: accept || 'application/json' }, timeout: TIMEOUT },
      (res) => {
        let body = ''
        res.on('data', (c) => (body += c))
        res.on('end', () => resolve({ status: res.statusCode, body, type: res.headers['content-type'] || '' }))
      },
    )
    r.on('timeout', () => r.destroy(Object.assign(new Error('timed out'), { code: 'ETIMEDOUT' })))
    r.on('error', reject)
    r.end()
  })
}

function encPath(p) {
  return p.replace(/^\/+|\/+$/g, '').split('/').map(encodeURIComponent).join('/')
}

function die(err) {
  const code = err?.code
  if (code === 'ECONNREFUSED' || code === 'ETIMEDOUT' || (code && code.includes('CERT'))) {
    console.error(`Vault not reachable (${code}). Run: node scripts/eamos-vault-mcp-preflight.mjs`)
    process.exit(2)
  }
  console.error(String(err?.message || err))
  process.exit(1)
}

function parse(body) {
  try {
    return JSON.parse(body)
  } catch {
    return null
  }
}

try {
  if (!cmd || cmd === 'help') {
    console.log('usage: eamos-vault <info|list [DIR]|read PATH|search QUERY> [--json]')
    process.exit(cmd ? 0 : 1)
  }

  if (cmd === 'info') {
    const res = await req('GET', '/')
    const j = parse(res.body)
    if (JSON_OUT) console.log(JSON.stringify(j, null, 2))
    else console.log(`${j?.service || 'obsidian'} v${j?.versions?.self || j?.version || '?'} · authenticated:${j?.authenticated}`)
    process.exit(0)
  }

  if (cmd === 'list') {
    const dir = rest[0] ? `/vault/${encPath(rest[0])}/` : '/vault/'
    const res = await req('GET', dir)
    if (res.status !== 200) die(new Error(`HTTP ${res.status} on ${dir}: ${res.body.slice(0, 200)}`))
    const j = parse(res.body)
    const files = j?.files || []
    if (JSON_OUT) console.log(JSON.stringify(files, null, 2))
    else {
      console.log(`${dir}  (${files.length})`)
      for (const f of files) console.log(`  ${f}`)
    }
    process.exit(0)
  }

  if (cmd === 'read') {
    if (!rest[0]) die(new Error('read needs a PATH'))
    const res = await req('GET', `/vault/${encPath(rest[0])}`, { accept: 'text/markdown' })
    if (res.status === 404) die(new Error(`not found: ${rest[0]}`))
    if (res.status !== 200) die(new Error(`HTTP ${res.status}: ${res.body.slice(0, 200)}`))
    if (JSON_OUT) console.log(JSON.stringify({ path: rest[0], content: res.body }, null, 2))
    else console.log(res.body)
    process.exit(0)
  }

  if (cmd === 'search') {
    const query = rest.join(' ')
    if (!query) die(new Error('search needs a QUERY'))
    const res = await req('POST', '/search/simple/', { query: { query, contextLength: 120 } })
    if (res.status !== 200) die(new Error(`HTTP ${res.status}: ${res.body.slice(0, 200)}`))
    const hits = parse(res.body) || []
    if (JSON_OUT) console.log(JSON.stringify(hits, null, 2))
    else {
      console.log(`"${query}" -> ${hits.length} hit(s)`)
      for (const h of hits.slice(0, 20)) {
        console.log(`  ${h.filename}${h.score != null ? `  (score ${h.score})` : ''}`)
        const ctx = (h.matches?.[0]?.context || '').replace(/\s+/g, ' ').trim()
        if (ctx) console.log(`    …${ctx.slice(0, 160)}…`)
      }
    }
    process.exit(0)
  }

  console.error(`unknown command: ${cmd}`)
  process.exit(1)
} catch (err) {
  die(err)
}
