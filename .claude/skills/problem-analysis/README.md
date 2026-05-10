<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Problem Analysis

Root cause identification workflow. Determines WHY a problem occurs, explicitly avoiding solution proposal.

## Overview

This skill distinguishes itself from solution evaluation. The five-phase approach (Gate, Hypothesize, Investigate, Formulate, Output) ensures problems are understood before fixes are considered.

## Key Design Principles

**Problem vs. Solution Framing**: Root causes must describe observable conditions rather than absences.

- Incorrect: "We don't have validation"
- Correct: "User input reaches processing without sanitization"

This distinction prevents presupposing specific remedies.

**Confidence Measurement**: Rather than relying on self-reported certainty, the skill uses four factual criteria: evidence citation, alternative hypothesis examination, symptom explanation completeness, and proper framing. A score of 4 points indicates HIGH confidence sufficient for downstream solution discovery.

**Multiple Hypotheses**: Generating 2-4 distinct explanations before investigation prevents confirmation bias, forcing comparative evaluation rather than tunnel vision.

**Iteration Management**: The investigation phase caps at 5 iterations -- enough for meaningful depth without infinite continuation. The script manages counting, preventing LLM miscounting.

## When to Use

- Problems reported but causes remain unclear
- Symptoms known but root mechanism unknown
- Before selecting a solution (must understand problem first)

## When NOT to Use

- Root cause already known (go directly to solution)
- Solution selection is the task (use decision-critic instead)
