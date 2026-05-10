<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# skills/

Script-based agent workflows with shared orchestration framework. Read `README.md` before modifying any skill code — it defines file ordering, prompt patterns, and naming conventions.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `README.md` | File organization, prompt patterns, naming, anti-patterns | BEFORE modifying any skill code |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `planner/` | Planning and execution workflows | Creating implementation plans |
| `refactor/` | Refactoring analysis across dimensions | Technical debt review, code quality |
| `problem-analysis/` | Structured problem decomposition | Understanding complex issues |
| `decision-critic/` | Decision stress-testing and critique | Validating architectural choices |
| `deepthink/` | Structured reasoning for open questions | Analytical questions without frameworks |
| `codebase-analysis/` | Systematic codebase exploration | Repository architecture review |
| `prompt-engineer/` | Prompt optimization and engineering | Improving agent prompts |
| `incoherence/` | Consistency detection | Finding spec/implementation mismatches |
| `doc-sync/` | Documentation synchronization | Syncing docs across repos |
| `scripts/` | Python implementation code for all skills | Modifying skill logic or adding a new skill |

## Script Invocation

```
python3 -m skills.<skill_name>.<module> --step 1
```
