<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
---
name: doc-sync
description: Synchronizes docs across a repository. Use when user asks to sync docs.
---

# Doc Sync

Audits and synchronizes the CLAUDE.md/README.md documentation hierarchy across a repository.

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

```
python3 -m skills.doc_sync.sync --step 1
```

Working directory: `.claude/skills/scripts`

## Workflow Phases

1. **Discovery** -- Maps directories requiring CLAUDE.md verification
2. **Audit** -- Detects drift and misplaced content
3. **Migration** -- Moves architectural content from CLAUDE.md to README.md
4. **Update** -- Creates/refreshes indexes with table-based format
5. **Verification** -- Confirms complete coverage and correct structure

## Key Distinctions

- CLAUDE.md: Navigation index + operational commands (copy-pasteable procedures)
- README.md: Architecture, design rationale, invariants, tradeoffs (invisible knowledge)
