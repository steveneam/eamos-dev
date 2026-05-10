# .claude/

Claude Code configuration: agent role definitions, universal conventions, output styles, and workflow skills.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `settings.json` | Project-level Claude Code settings: hooks, permissions | Changing hooks or project permissions |
| `settings.local.json` | Local overrides (gitignored) | Local-only permission or hook changes |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `agents/` | Custom subagent role definitions (architect, developer, debugger, etc.) | Configuring or understanding agent roles |
| `conventions/` | Universal coding and documentation standards | Code review, documentation, writing CLAUDE.md/README.md |
| `output-styles/` | Output format instructions for agent responses | Changing how agents format their output |
| `skills/` | Workflow skill scripts (planner, deepthink, refactor, doc-sync, etc.) | Running or modifying a skill |
