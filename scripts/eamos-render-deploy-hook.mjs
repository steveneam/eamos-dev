#!/usr/bin/env node

import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

function parseArgs(argv) {
  const args = {
    hookFile: '.render-deploy-hook',
    dryRun: false,
  }
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index]
    if (arg === '--hook-file') {
      const value = argv[index + 1]
      if (!value) throw new Error('--hook-file requires a path')
      args.hookFile = value
      index += 1
      continue
    }
    if (arg === '--dry-run') {
      args.dryRun = true
      continue
    }
    if (arg === '--help' || arg === '-h') {
      printHelp()
      process.exit(0)
    }
    throw new Error(`Unknown argument: ${arg}`)
  }
  return args
}

function printHelp() {
  console.log(`Usage: node scripts/eamos-render-deploy-hook.mjs [--hook-file PATH] [--dry-run]

Reads a local Render deploy hook file, ignores blank/comment lines, validates that
exactly one HTTPS hook URL remains, and POSTs it without printing the secret URL.`)
}

function parseHookFile(text) {
  const urls = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'))

  if (urls.length !== 1) {
    throw new Error(`Expected exactly one non-comment hook URL, found ${urls.length}`)
  }

  let url
  try {
    url = new URL(urls[0])
  } catch {
    throw new Error('Hook file contains an invalid URL')
  }
  if (url.protocol !== 'https:') {
    throw new Error('Render deploy hook must use HTTPS')
  }
  if (!/\.onrender\.com$/i.test(url.hostname) && !/render\.com$/i.test(url.hostname)) {
    throw new Error('Hook URL host is not a Render host')
  }
  return url
}

function sanitizePayload(payload) {
  if (!payload || typeof payload !== 'object') return {}
  const deploy = payload.deploy && typeof payload.deploy === 'object' ? payload.deploy : payload
  return {
    id: deploy.id ?? payload.id ?? null,
    status: deploy.status ?? payload.status ?? null,
    service_id: deploy.serviceId ?? deploy.service_id ?? payload.serviceId ?? payload.service_id ?? null,
    commit_id: deploy.commit?.id ?? deploy.commitId ?? payload.commitId ?? null,
    message: deploy.commit?.message ?? payload.message ?? null,
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  const hookFile = resolve(args.hookFile)
  const text = await readFile(hookFile, 'utf8')
  const hookUrl = parseHookFile(text)

  if (args.dryRun) {
    console.log(
      JSON.stringify(
        {
          status: 'ok',
          action: 'validated',
          hook_file: args.hookFile,
          hook_url_redacted: true,
        },
        null,
        2,
      ),
    )
    return
  }

  const response = await fetch(hookUrl, { method: 'POST' })
  const bodyText = await response.text()
  let payload = null
  if (bodyText.trim()) {
    try {
      payload = JSON.parse(bodyText)
    } catch {
      payload = { body_excerpt: bodyText.slice(0, 300) }
    }
  }

  const output = {
    status: response.ok ? 'triggered' : 'failed',
    http_status: response.status,
    hook_file: args.hookFile,
    hook_url_redacted: true,
    deploy: sanitizePayload(payload),
  }
  console.log(JSON.stringify(output, null, 2))

  if (!response.ok) {
    process.exitCode = 1
  }
}

main().catch((error) => {
  console.error(
    JSON.stringify(
      {
        status: 'failed',
        error: error instanceof Error ? error.message : String(error),
      },
      null,
      2,
    ),
  )
  process.exitCode = 1
})
