<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Codebase Analysis

Understanding-focused skill that builds systematic, evidence-backed comprehension of a codebase.

## Overview

Before planning anything non-trivial, you need to actually understand the codebase. Not impressions -- evidence. This skill forces systematic investigation with structured phases and explicit evidence requirements.

## Workflow Phases

| Phase                  | Actions                                                                        |
| ---------------------- | ------------------------------------------------------------------------------ |
| Exploration            | Delegate to Explore agent; process structure, tech stack, patterns             |
| Focus Selection        | Classify areas (architecture, performance, security, quality); assign P1/P2/P3 |
| Investigation Planning | Commit to specific files and questions; create accountability contract         |
| Deep Analysis          | Progressive investigation; document with file:line + quoted code               |
| Verification           | Audit completeness; ensure all commitments addressed                           |
| Synthesis              | Consolidate by severity; provide prioritized recommendations                  |

## When to Use

Four scenarios where this skill provides value:

- **Unfamiliar codebase** -- You cannot plan what you do not understand. Period.
- **Security review** -- Vulnerability assessment requires systematic coverage, not "I looked around and it seems fine."
- **Performance analysis** -- Before optimization, know where time actually goes, not where you assume it goes.
- **Architecture evaluation** -- Major refactors deserve evidence-backed understanding, not vibes.

## When to Skip

- You already understand the codebase well
- Simple bug fix with obvious scope
- User has provided comprehensive context

## Output

Findings organized by severity (CRITICAL/HIGH/MEDIUM/LOW), each with file:line references and quoted code. This feeds directly into planning -- you have evidence-backed understanding before proposing changes.
