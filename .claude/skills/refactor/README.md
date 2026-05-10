<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Refactor

LLM-generated code accumulates technical debt faster than hand-written code. The LLM does not see duplication across files. It does not notice god functions growing. It cannot detect that three modules implement the same validation logic differently.

This skill catches what the LLM misses. It explores multiple smell categories in parallel, validates findings against evidence, and outputs prioritized work items.

## Workflow

```
refactor.py                          explore.py (x10 parallel)
===========                          =========================

Step 1: Dispatch -----------------> Step 1: Domain Context
        (launch 10 explore agents)  Step 2: Principle + Violations
                                    Step 3: Pattern Generation
                                    Step 4: Search
                                    Step 5: Synthesis
                                           |
        <------------------------------<---+
        (collect smell_reports)

Step 2: Triage
        (structure findings with IDs)

Step 3: Cluster
        (group by shared root cause)

Step 4: Contextualize
        (extract user intent, prioritize)

Step 5: Synthesize
        (generate work items)
```

## Design Decisions

### Five-Step Explore Workflow

The original 2-step explore workflow conflated multiple cognitive tasks. LLMs perform better when each cognitive task gets focused attention:

- Step 1: Domain Context -- understand the project before analyzing it
- Step 2: Principle Extract -- understand the smell before hunting for it
- Step 3: Pattern Generate -- translate abstract hints to project-specific patterns
- Step 4: Search -- execute with generated patterns
- Step 5: Synthesis -- format findings

### Domain Context Per-Category

Each explore agent does its own domain context analysis, rather than lifting it to the parent. Different smell categories need different domain context aspects.

### Grep-Hints as Exemplars

The markdown files contain generic patterns. Using these literally would miss project-specific equivalents. The skill treats grep-hints as abstract exemplars that must be translated to project-specific equivalents based on domain context.

## What It Does NOT Do

- Generate refactored code (recommendations only)
- Run linters or static analysis
- Apply style fixes
- Propose changes beyond what evidence supports
