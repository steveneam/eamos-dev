#!/usr/bin/env node

import { existsSync } from 'node:fs'
import { readFile, rm } from 'node:fs/promises'
import { dirname, isAbsolute, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const EXPECTED_ROOT_PROJECT = {
  projectName: 'eamos-dev',
  projectId: 'prj_PbmfuQv2xsaXdh92MdNkeelm19yM',
}

function parseArgs(argv) {
  return {
    fix: argv.includes('--fix'),
    requireRootLink: argv.includes('--require-root-link'),
    help: argv.includes('--help') || argv.includes('-h'),
  }
}

function printHelp() {
  console.log(`Usage: node scripts/eamos-vercel-project-guard.mjs [--fix] [--require-root-link]

Fails if app/web/.vercel exists, because that nested link can target the wrong
Vercel project. Also validates the repo-root .vercel link when present.

Options:
  --fix                Remove app/web/.vercel after validating it is inside this repo.
  --require-root-link  Fail when the repo-root .vercel/project.json is missing.`)
}

function safeRelative(root, target) {
  const rel = relative(root, target)
  return Boolean(rel) && !rel.startsWith('..') && !isAbsolute(rel)
}

async function readProjectJson(projectFile) {
  const raw = await readFile(projectFile, 'utf8')
  try {
    return JSON.parse(raw)
  } catch (error) {
    throw new Error(`${projectFile} is not valid JSON: ${error instanceof Error ? error.message : String(error)}`)
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (args.help) {
    printHelp()
    return
  }

  const scriptsDir = dirname(fileURLToPath(import.meta.url))
  const repoRoot = resolve(scriptsDir, '..')
  const rootProjectFile = join(repoRoot, '.vercel', 'project.json')
  const nestedVercelDir = join(repoRoot, 'app', 'web', '.vercel')
  const nestedProjectFile = join(nestedVercelDir, 'project.json')

  const errors = []
  const notes = []

  if (existsSync(nestedVercelDir)) {
    let nestedLabel = 'unknown project'
    if (existsSync(nestedProjectFile)) {
      try {
        const nested = await readProjectJson(nestedProjectFile)
        nestedLabel = `${nested.projectName ?? 'unknown'} (${nested.projectId ?? 'unknown id'})`
      } catch (error) {
        nestedLabel = error instanceof Error ? error.message : String(error)
      }
    }

    if (args.fix) {
      const resolvedNested = resolve(nestedVercelDir)
      if (!safeRelative(repoRoot, resolvedNested)) {
        throw new Error(`Refusing to remove path outside repo: ${resolvedNested}`)
      }
      await rm(resolvedNested, { recursive: true, force: true })
      notes.push(`removed nested app/web/.vercel link (${nestedLabel})`)
    } else {
      errors.push(
        `app/web/.vercel exists and points at ${nestedLabel}. Remove it; Eamos deploys must use the repo-root .vercel link.`,
      )
    }
  }

  if (!existsSync(rootProjectFile)) {
    const message = 'repo-root .vercel/project.json is missing; run Vercel commands from the repo root after linking eamos-dev'
    if (args.requireRootLink) errors.push(message)
    else notes.push(message)
  } else {
    const rootProject = await readProjectJson(rootProjectFile)
    // projectId is the authoritative link identifier — always enforce it.
    // projectName is only present in a locally-linked .vercel/project.json; Vercel's
    // build infra regenerates the file with projectId + orgId only (no projectName),
    // so a name check there always fails spuriously. Only enforce the name when present.
    const idMismatch = rootProject.projectId !== EXPECTED_ROOT_PROJECT.projectId
    const nameMismatch =
      rootProject.projectName != null &&
      rootProject.projectName !== EXPECTED_ROOT_PROJECT.projectName
    if (idMismatch || nameMismatch) {
      errors.push(
        `repo-root .vercel points at ${rootProject.projectName ?? 'unknown'} (${rootProject.projectId ?? 'unknown id'}), expected ${EXPECTED_ROOT_PROJECT.projectName} (${EXPECTED_ROOT_PROJECT.projectId})`,
      )
    } else {
      notes.push(`repo-root Vercel link OK: ${rootProject.projectName ?? EXPECTED_ROOT_PROJECT.projectName}`)
    }
  }

  if (errors.length > 0) {
    console.error(
      JSON.stringify(
        {
          status: 'failed',
          errors,
          fix: 'Run: node scripts/eamos-vercel-project-guard.mjs --fix',
        },
        null,
        2,
      ),
    )
    process.exitCode = 1
    return
  }

  console.log(JSON.stringify({ status: 'ok', notes }, null, 2))
}

main().catch((error) => {
  console.error(JSON.stringify({ status: 'failed', error: error instanceof Error ? error.message : String(error) }, null, 2))
  process.exitCode = 1
})
