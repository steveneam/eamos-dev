<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
---
name: codebase-analysis
description: Invoke IMMEDIATELY via python script when user requests codebase understanding, architecture comprehension, or repository orientation. Do NOT explore first - the script orchestrates exploration.
---

# Codebase Analysis

Understanding-focused skill that builds foundational comprehension of codebase structure, patterns, flows, decisions, and context. Serves as foundation for downstream analysis skills (problem-analysis, refactor, etc.).

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

```
python3 -m skills.codebase_analysis.analyze --step 1
```

Working directory: `.claude/skills/scripts`

Do NOT explore first. Run the script and follow its output.
