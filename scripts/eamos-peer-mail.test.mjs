import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import {
  appendFileSync,
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { execFileSync } from 'node:child_process'
import { join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { fileURLToPath } from 'node:url'
import {
  PeerMailError,
  checkMailbox,
  clearSafeReport,
  loadRegistry,
  selectMailbox,
  sendMessage,
  stagingGuard,
  statusReport,
  waitForMailbox,
} from './eamos-peer-mail.mjs'

const HERE = resolve(fileURLToPath(new URL('.', import.meta.url)))
const tempRoots = []

afterEach(() => {
  while (tempRoots.length) rmSync(tempRoots.pop(), { recursive: true, force: true })
})

function git(root, ...args) {
  return execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
}

function write(path, contents) {
  mkdirSync(resolve(path, '..'), { recursive: true })
  writeFileSync(path, contents, 'utf8')
}

function registryFixture() {
  return {
    version: 1,
    local: { id: 'alpha', label: 'alpha', signature: 'Alpha' },
    defaults: { lockTtlSeconds: 60, pollIntervalSeconds: 0.01, maxMessageBytes: 4096 },
    mailboxes: [
      {
        id: 'bravo',
        peer: { id: 'bravo', label: 'bravo' },
        owners: { outbound: 'alpha', inbound: 'bravo' },
        outbound: {
          path: 'agent_handoff/TO-BRAVO.md',
          headingLevel: 2,
          appendMarker: '_Append below._',
        },
        inbound: { path: 'agent_handoff/FROM-BRAVO.md', headingLevels: [1, 2] },
        allowDirtyInbound: true,
      },
    ],
  }
}

function currentMarkdown(lock = 'UNLOCKED · 2026-07-16 12:00 +0000 · Alpha') {
  return `# Current Agent State

## Active Status

- **Alpha:** STOPPED at a verified boundary.

## Log Edit-Lock

${lock}

## Resume Prompt

\`\`\`text
# Resume prompt · 2026-07-16 12:00 +0000 · Alpha next slice
Read the peer-mail contract and the current landing plan.
Continue the verified next slice without touching peer-owned mail.
Safe to clear: yes.
\`\`\`

## Pointer

- The coordination ratchet is committed on the current branch.

## Delta

- Mock peer-mail verification is green.

## Next Action

- Implement the approved landing feature gallery from reproducible demo captures.
`
}

function makeRepo({ withRemote = false } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'eamos-peer-mail-'))
  tempRoots.push(root)
  git(root, 'init', '-b', 'main')
  git(root, 'config', 'user.email', 'tests@example.invalid')
  git(root, 'config', 'user.name', 'Peer Mail Tests')
  write(join(root, '.agent-mailboxes.json'), `${JSON.stringify(registryFixture(), null, 2)}\n`)
  write(
    join(root, 'agent_handoff', 'TO-BRAVO.md'),
    '# Outbound to Bravo\n\n_Append below._\n\n## 2026-07-16 08:00 UTC · alpha → bravo — Initial\n\nReady.\n',
  )
  write(
    join(root, 'agent_handoff', 'FROM-BRAVO.md'),
    '# From Bravo (2026-07-16 08:05 UTC)\n\nInitial reply.\n',
  )
  write(join(root, 'agent_handoff', 'CURRENT.md'), currentMarkdown())
  mkdirSync(join(root, 'scripts'), { recursive: true })
  copyFileSync(join(HERE, 'eamos-handoff-lint.mjs'), join(root, 'scripts', 'eamos-handoff-lint.mjs'))
  git(root, 'add', '--', '.agent-mailboxes.json', 'agent_handoff', 'scripts/eamos-handoff-lint.mjs')
  git(root, 'commit', '-m', 'test: seed mock mailboxes')
  if (withRemote) {
    const remote = mkdtempSync(join(tmpdir(), 'eamos-peer-mail-remote-'))
    tempRoots.push(remote)
    execFileSync('git', ['init', '--bare', remote], { encoding: 'utf8' })
    git(root, 'remote', 'add', 'origin', remote)
    git(root, 'push', '-u', 'origin', 'main')
  }
  return root
}

test('registry enforces local outbound ownership and repository-contained paths', () => {
  const root = makeRepo()
  const path = join(root, '.agent-mailboxes.json')
  const invalidOwner = registryFixture()
  invalidOwner.mailboxes[0].owners.outbound = 'bravo'
  writeFileSync(path, `${JSON.stringify(invalidOwner)}\n`)
  assert.throws(() => loadRegistry({ root }), (error) => error instanceof PeerMailError && error.code === 'INVALID_CONFIG')

  const escaping = registryFixture()
  escaping.mailboxes[0].outbound.path = '../outside.md'
  writeFileSync(path, `${JSON.stringify(escaping)}\n`)
  assert.throws(() => loadRegistry({ root }), (error) => error instanceof PeerMailError && error.code === 'INVALID_CONFIG')
})

test('send appends one UTC-ordered message under the local ownership contract', () => {
  const root = makeRepo()
  const registry = loadRegistry({ root })
  const mailbox = selectMailbox(registry, 'bravo')
  const before = readFileSync(mailbox.outbound.absolute, 'utf8')
  const result = sendMessage(registry, mailbox, {
    subject: 'Verification ready',
    body: 'All mock checks passed. No external action ran.',
    now: new Date('2026-07-16T09:15:00Z'),
  })
  const after = readFileSync(mailbox.outbound.absolute, 'utf8')
  assert.equal(result.ok, true)
  assert.ok(after.startsWith(before))
  assert.match(after, /## 2026-07-16 09:15 UTC · alpha → bravo — Verification ready/)
  assert.match(after, /— Alpha\n$/)
  assert.equal(statusReport(registry).ok, true)
})

test('send rejects secret-shaped content without changing the mailbox', () => {
  const root = makeRepo()
  const registry = loadRegistry({ root })
  const mailbox = selectMailbox(registry, 'bravo')
  const before = readFileSync(mailbox.outbound.absolute, 'utf8')
  assert.throws(
    () => sendMessage(registry, mailbox, {
      subject: 'Unsafe payload',
      body: 'api_key=abcdefghijklmnop',
      now: new Date('2026-07-16T09:15:00Z'),
    }),
    (error) => error instanceof PeerMailError && error.code === 'SECRET_DETECTED',
  )
  assert.equal(readFileSync(mailbox.outbound.absolute, 'utf8'), before)
})

test('peer-owned inbound staging blocks send and is reported by the staging guard', () => {
  const root = makeRepo()
  const registry = loadRegistry({ root })
  const mailbox = selectMailbox(registry, 'bravo')
  appendFileSync(mailbox.inbound.absolute, '\nPeer update.\n')
  git(root, 'add', '--', mailbox.inbound.relative)
  const guard = stagingGuard(registry)
  assert.deepEqual(guard.violations, [mailbox.inbound.relative])
  assert.throws(
    () => sendMessage(registry, mailbox, {
      subject: 'Should fail',
      body: 'The staged peer file must block this write.',
      now: new Date('2026-07-16T09:15:00Z'),
    }),
    (error) => error instanceof PeerMailError && error.code === 'STAGING_GUARD',
  )
})

test('check acknowledges by fingerprint without editing the inbound mailbox', () => {
  const root = makeRepo()
  const registry = loadRegistry({ root })
  const mailbox = selectMailbox(registry, 'bravo')
  const before = readFileSync(mailbox.inbound.absolute, 'utf8')
  assert.equal(checkMailbox(registry, mailbox).changed, true)
  assert.equal(checkMailbox(registry, mailbox, { acknowledge: true }).acknowledged, true)
  assert.equal(checkMailbox(registry, mailbox).changed, false)
  assert.equal(readFileSync(mailbox.inbound.absolute, 'utf8'), before)
})

test('check reports the physically latest accepted inbound heading when peer timestamps regress', () => {
  const root = makeRepo()
  const registry = loadRegistry({ root })
  const mailbox = selectMailbox(registry, 'bravo')
  appendFileSync(
    mailbox.inbound.absolute,
    '\n## 2026-07-16 08:10 UTC · bravo → alpha — First append\n\nFirst.\n' +
      '\n## 2026-07-16 08:09 UTC · bravo → alpha — Delayed append\n\nSecond.\n',
  )

  const result = checkMailbox(registry, mailbox)

  assert.match(result.latestHeading, /Delayed append/)
})

test('wait detects a new peer append without acknowledging or modifying it', async () => {
  const root = makeRepo()
  const registry = loadRegistry({ root })
  const mailbox = selectMailbox(registry, 'bravo')
  setTimeout(() => {
    appendFileSync(
      mailbox.inbound.absolute,
      '\n## Follow-up (2026-07-16 08:06 UTC)\n\nA bounded update.\n',
    )
  }, 30)
  const result = await waitForMailbox(registry, mailbox, { timeoutSeconds: 1, intervalSeconds: 0.01 })
  assert.equal(result.changed, true)
  assert.match(result.latestHeading, /Follow-up/)
})

test('status reports stale mailbox locks and never removes them implicitly', () => {
  const root = makeRepo()
  const registry = loadRegistry({ root })
  const lockDirectory = resolve(root, git(root, 'rev-parse', '--git-path', 'eamos-peer-mail/locks'))
  mkdirSync(lockDirectory, { recursive: true })
  const lockPath = join(lockDirectory, 'bravo.lock')
  writeFileSync(lockPath, `${JSON.stringify({
    version: 1,
    mailbox: 'bravo',
    owner: 'alpha',
    pid: 1,
    createdAt: '2026-07-16T08:00:00.000Z',
  })}\n`)
  const report = statusReport(registry, { now: new Date('2026-07-16T09:00:01.000Z') })
  assert.equal(report.ok, false)
  assert.ok(report.issues.some((issue) => issue.code === 'STALE_LOCK'))
  assert.equal(readFileSync(lockPath, 'utf8').includes('bravo'), true)
})

test('clear-safe accepts an unstaged peer update but refuses staged or local dirt', () => {
  const root = makeRepo({ withRemote: true })
  const registry = loadRegistry({ root })
  const mailbox = selectMailbox(registry, 'bravo')
  assert.equal(clearSafeReport(registry).ok, true)

  appendFileSync(mailbox.inbound.absolute, '\n# Peer update (2026-07-16 09:00 UTC)\n\nExternal state.\n')
  const withPeerUpdate = clearSafeReport(registry)
  assert.equal(withPeerUpdate.ok, true)
  assert.deepEqual(withPeerUpdate.evidence.allowedDirtyInbound, [mailbox.inbound.relative])

  git(root, 'add', '--', mailbox.inbound.relative)
  const staged = clearSafeReport(registry)
  assert.equal(staged.ok, false)
  assert.ok(staged.issues.some((issue) => issue.code === 'STAGED_PEER_FILE'))
  git(root, 'restore', '--staged', '--', mailbox.inbound.relative)

  writeFileSync(join(root, 'agent_handoff', 'CURRENT.md'), currentMarkdown('LOCKED: 2026-07-16 12:00 +0000 · Alpha'))
  const locked = clearSafeReport(registry)
  assert.equal(locked.ok, false)
  assert.ok(locked.issues.some((issue) => issue.code === 'HANDOFF_LOCKED'))
  assert.ok(locked.issues.some((issue) => issue.code === 'UNCOMMITTED'))
})
