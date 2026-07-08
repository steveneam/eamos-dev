# Archived Codex Handoff - Obsidian MCP Env/TLS Discovery

Archived from `agent_handoff/CURRENT.md` on 2026-07-04 19:51 +1000 by Codex before replacing the live Codex section with the backend/report materialisation audit handoff.

## Codex - Last Task & Resume

Owner-written by **Codex only**. Claude: read, never rewrite (README Rule 1/2).
Section last edited: 2026-07-04 19:39 +1000 - Codex.

**Latest Codex update (2026-07-04 19:39 +1000 - Codex):**
Verified the Obsidian MCP state from a fresh VS Code/Codex session, then used
the vault's native MCP endpoint directly to find the startup failure mode.

Findings:

- Tool discovery for exact `obsidian-vault` names and read-helper names returns
  zero tools in this session; a broad `obsidian` discovery query also returns
  zero.
- `codex mcp get obsidian-vault --json` still confirms the global streamable
  HTTP server at `https://127.0.0.1:27124/mcp`, bearer-env auth through
  `OBSIDIAN_API_KEY`, and the read/search/list/path allowlist:
  `vault_read`, `vault_list`, `vault_get_document_map`, `search_simple`,
  `search_query`, `tag_list`, `command_list`, `active_file_get_path`, and
  `periodic_note_get_path`.
- Direct MCP access to Obsidian works when Windows user-level env vars are
  injected into a child process: `initialize` returns
  `obsidian-local-rest-api` v1.0.0 and `tools/list` returns 16 server tools.
  Only read/search/list/path tools were used; write/execute/open tools were
  not called.
- The relevant vault note is `Forj/Wiki/reference/vault-mcp-wiring.md`. It
  records the native Local REST API `/mcp` endpoint as primary and calls out
  the load-bearing HTTPS self-signed-cert requirement: consumers need both
  `OBSIDIAN_API_KEY` and `NODE_EXTRA_CA_CERTS` in the process environment at
  MCP startup.
- This active Codex process inherited neither `OBSIDIAN_API_KEY` nor
  `NODE_EXTRA_CA_CERTS`; the Windows user-level vars are present, the cert path
  exists, and a child Node process using those user-level vars connects over
  trusted HTTPS without disabling TLS.
- Interpretation: repo/global MCP registration and Obsidian's server are
  healthy. The missing Codex namespace is most likely process-environment
  inheritance at the VS Code/Codex host boundary. The next proof is a full
  quit of all Code/Codex host processes, relaunch from an environment containing
  both vars, then repeat tool discovery.
- Search 7/8 remains closed. Local `main` matches `origin/main` at `436721e`
  (`docs(search): close Search 7/8 cleanup`).

No deploy/env/provider flip, Supabase mutation, source materialization/download/
upload, destructive git, Obsidian write-tool call/allowlisting, or secret
output occurred.

**Latest resume prompt:**
```text
# Resume prompt · 2026-07-04 19:39 +1000 · Codex Obsidian MCP env/TLS discovery
Eamos. Read AGENTS.md, CODEX.md, agent_handoff/README.md, agent_handoff/CURRENT.md, agent_handoff/RISKS.md, PROGRESS.md top, COORDINATION.md, docs/parallel-agents/{retrofit-notes,ratchet-philosophy}.md, docs/search-results-and-answer-hardening/{design,spec,plan}.md, docs/search-index/{spec,plan}.md, then git status --short --branch.
Delta: Fresh VS Code/Codex session still exposes no callable `obsidian-vault` namespace. Direct vault MCP works when Windows user-level `OBSIDIAN_API_KEY` + `NODE_EXTRA_CA_CERTS` are injected; vault note `Forj/Wiki/reference/vault-mcp-wiring.md` identifies this exact env/TLS startup requirement. This active Codex process inherited neither env var, while user env + cert file are present. Search 7/8 remains closed at `origin/main` `436721e`.
Next: fully quit all Code/Codex host processes, relaunch from an environment containing both vars, then repeat tool discovery; otherwise choose the next backend/search slice or deploy gate.
Guardrails: keep Search auth-required/read-only unless explicitly changed; no env/provider flips, Supabase mutation, runtime seed/sync, source materialization/download/upload, deploy hook use, destructive git, secret output, or Obsidian write/execute/open tool use/allowlisting unless explicitly approved.
End clear-safe with a fresh stamped resume prompt.
```
