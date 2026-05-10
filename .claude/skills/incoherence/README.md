<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Incoherence Detection

Detects and resolves incoherence in documentation, code, and specs vs implementation.

## Overview

The agent is a WORKFLOW EXECUTOR for this skill. The script IS the workflow. Following it exactly IS being helpful.

Deviating from the script HARMS the user:

- Skipping steps removes their interactive control
- Summarizing instead of continuing breaks the resolution flow
- Fixing issues directly bypasses their decision-making

Correct: After step 12, invoke step 13 with findings.
Incorrect: After step 12, present a summary to the user.

## Three Phases

1. **Detection** (steps 1-12): Survey, explore, verify candidates
2. **Resolution** (steps 13-15): Interactive AskUserQuestion prompts
3. **Application** (steps 16-21): Apply changes, present final report

Resolution is interactive -- user answers structured questions inline. No manual file editing required.

## What It Detects

- Documentation contradicting implementation
- Specs describing behavior the code doesn't implement
- Configuration options code doesn't use
- Interface contracts violated by implementations
- Naming inconsistencies between layers
