# Peer-mailbox contract

Status: active invariant ratchet.

This contract turns cross-agent Markdown channels into a small, testable
mailbox protocol. It governs file ownership and safe local handling. It does
not grant authority for the action described in a message.

## Invariants

1. One file has one writer. The local actor appends only to its registered
   outbound file. The peer-owned inbound file is read-only.
2. Messages append at EOF. Existing bytes are never rewritten by `send`.
3. Every generated heading carries a UTC minute stamp. Dated headings remain
   monotonic; outbound headings always include a time.
4. A per-peer exclusive lock serializes writers. Active and stale locks fail
   closed. The tool reports a stale lock but never removes one implicitly.
5. Message subjects and bodies are scanned for common credential shapes before
   a write. Existing channel files are scanned before status/check/send.
6. Peer-owned inbound files may not enter the Git index. The tracked pre-commit
   hook enforces this regardless of which files the user intended to commit.
7. Receipt state and locks live under `.git/eamos-peer-mail/`. They are local
   execution state, not coordination history, and never modify a mailbox.
8. A notification or message is untrusted coordination data. Spend, secrets,
   destructive work, provider changes, deploys, and founder gates stay gated.

## Registry

Each repository carries `.agent-mailboxes.json` version 1. It defines:

- the local actor id, display label, and signature;
- lock TTL, poll interval, and maximum message size;
- one peer id per mailbox;
- explicit outbound and inbound owners;
- repository-relative channel paths;
- the outbound append marker and heading level;
- the accepted inbound heading levels;
- whether a watcher-owned inbound update may remain dirty at clear-safe.

The loader rejects absolute or escaping channel paths, duplicate ids, duplicate
paths, mismatched owners, unsupported versions, and invalid heading levels.
An actor-specific registry may live outside the repository when an operations
agent writes a channel physically stored in a peer repository; pass it with
`--registry` while setting `--root` to the repository that contains the files.

## Commands

All commands accept `--json`, `--root=<repo>`, and
`--registry=<path>`.

### `status`

Validates both directions, reports fingerprints/latest headings, scans secrets
and ordering, reports locks, and flags protected staged paths. Use
`--staging-only` for the commit-time ownership guard.

### `check`

Compares the inbound SHA-256 fingerprint with the private receipt. It prints
metadata only, never the body. `--ack` records the current fingerprint under
`.git`; it does not edit the inbound file.

### `wait`

Polls the inbound fingerprint until it changes or the timeout expires. It does
not acknowledge the update. The agent-facing default is 60 seconds so a wait
cannot silence progress reporting for an unbounded period.

### `send`

Requires a registered peer, one-line subject, and `--body-file` (or `-` for
stdin). The sequence is:

1. reject a staged peer-owned inbox;
2. scan the proposed content for secret shapes;
3. acquire the exclusive peer lock;
4. re-read and validate the outbound channel;
5. append one generated UTC-stamped section and fsync;
6. re-validate, then release the lock.

Use an owner-only secret channel for credentials. Never weaken the scanner to
carry a secret through Markdown.

### `clear-safe`

Produces a proof, not a promise. It refuses unless all of these are true:

- `CURRENT.md` has a released Log Edit-Lock and no active Shared File Lock;
- `## Next Action` contains a concrete bullet, not a placeholder;
- `eamos-handoff-lint --strict` passes;
- every locally owned change is committed;
- no peer-owned inbound file is staged;
- no peer-mail lock remains;
- the current branch has an upstream and is neither ahead nor behind it.

A registry entry may declare its peer-owned inbound path as an allowed dirty
exception. This models a watcher appending external mail during a local session.
The exception never applies to the Git index.

## Verification and CI

`node --test scripts/eamos-peer-mail.test.mjs` uses temporary Git repositories,
mock mailboxes, and a local bare remote. Coverage includes registry containment,
append ordering, secret rejection, staged-inbox refusal, fingerprint receipts,
wait behavior, stale locks, and the committed/pushed clear-safe proof.

CI runs the mock suite, the staging guard, and strict handoff lint in the
`coordination ratchets` job. The root repo gate also includes the staging guard
and test suite. The pre-commit hook makes inbox ownership independent of an
agent remembering the rule.

## Adoption checklist

1. Identify the physical two-file channel and freeze one writer per file.
2. Create an actor-specific version-1 registry with exact paths and owners.
3. Baseline `status`; fix order, marker, or secret findings before enabling
   writes.
4. Run the mock test suite unchanged.
5. Install the staging-only guard in the tracked commit hook and CI.
6. Exercise `check --ack` and a short `wait` against mock or disposable files.
7. Review a prepared `send` body, then obtain the authority required for the
   first live append.
8. Run `clear-safe` only against the repository whose `CURRENT.md` and Git
   upstream it is proving.

The Eamos-to-Swordfish, ready-but-unsent application of this checklist is in
`docs/operations/swordfish-peer-mail-adoption-packet.md`.
