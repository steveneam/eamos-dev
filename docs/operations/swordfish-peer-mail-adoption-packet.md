# Swordfish peer-mail adoption packet

Status: ready for review, deliberately unsent.
Prepared: 2026-07-16 11:36 +0000 by Codex.

This packet proposes an executable layer around Swordfish's existing watcher.
It does not modify Swordfish, contact its agent, install a service, or change
the watcher timer.

## Existing contract observed read-only

- Swordfish watches Eamos's
  `agent_handoff/ASK-BACKS-FOR-SWORDFISH.md` every ten minutes.
- It records a SHA-256 baseline and writes `NEW-eamos` on change.
- Swordfish writes replies to Eamos's
  `agent_handoff/FROM-SWORDFISH.md`.
- Notifications are explicitly non-authoritative.
- The current shell watcher extracts only `# ` headings, while Eamos outbound
  messages use `## ` headings. The hash still triggers correctly, but the alert
  label can fall back to the page title instead of the newest message subject.

## Proposed bounded adoption

1. Keep `setup-peer-mail-watch.sh`, its systemd timer, Telegram path, and state
   directory unchanged for the first pass.
2. Vendor the neutral behavior from `scripts/eamos-peer-mail.mjs` and its mock
   test into Swordfish under Swordfish-owned names.
3. Store an untracked root-owned actor registry at
   `/etc/swordfish/peer-mail/eamos-registry.json`. Run it with Eamos's repository
   as `--root`. Reciprocal ownership is:

```json
{
  "version": 1,
  "local": { "id": "swordfish", "label": "swordfish", "signature": "Swordfish" },
  "defaults": { "lockTtlSeconds": 1200, "pollIntervalSeconds": 5, "maxMessageBytes": 65536 },
  "mailboxes": [
    {
      "id": "eamos",
      "peer": { "id": "eamos", "label": "eamos" },
      "owners": { "outbound": "swordfish", "inbound": "eamos" },
      "outbound": {
        "path": "agent_handoff/FROM-SWORDFISH.md",
        "headingLevel": 1,
        "appendMarker": "---"
      },
      "inbound": {
        "path": "agent_handoff/ASK-BACKS-FOR-SWORDFISH.md",
        "headingLevels": [2]
      },
      "allowDirtyInbound": true
    }
  ]
}
```

4. Baseline only with read-only commands:

```text
node <swordfish-vendored-cli> status \
  --root=/home/deploy/work/eamos \
  --registry=/etc/swordfish/peer-mail/eamos-registry.json
node <swordfish-vendored-cli> check --peer=eamos --ack \
  --root=/home/deploy/work/eamos \
  --registry=/etc/swordfish/peer-mail/eamos-registry.json
```

5. Do not use `clear-safe` with Eamos as `--root`; that command proves the
   selected repository's handoff and upstream. Swordfish should port the same
   check separately against its own `CURRENT.md` and repository.
6. After mock tests and read-only baselining pass, review one disposable-channel
   send. A live reply remains separately authorized by the active coordination
   task.
7. In a later watcher-only patch, change newest-heading extraction to accept
   both `# ` and `## ` so the Telegram label names the newest Eamos section.
   Preserve printable-character filtering and the 80-character cap.

## Acceptance evidence

- mock tests pass without reading or writing live channel files;
- live `status` is clean and reports the existing channel fingerprints;
- `check --ack` changes only private receipt state;
- a staged Eamos-owned ask-back is rejected from a Swordfish commit context;
- active and stale locks both fail closed;
- a secret-shaped disposable body is rejected without a write;
- the existing timer and Telegram notification still fire from a plain hash
  change after adoption.

## Held actions

Do not run the commands above, edit either live channel, patch Swordfish, or
install/restart its watcher from this packet. Those actions require a new,
explicitly assigned Swordfish-side slice.
