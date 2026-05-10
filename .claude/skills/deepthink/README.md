<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# DeepThink

Structured reasoning framework for open-ended analytical questions where the answer structure itself is unknown.

## Overview

Handles taxonomy design, conceptual analysis, trade-off exploration, and definitional questions -- problems that resist predefined frameworks.

## Workflow Structure

Two operational modes: Full (14 steps) and Quick (8 steps).

Process flow: Input Processing -> Problem Understanding -> Planning -> Sub-Agent Design -> Divergent Exploration -> Convergent Synthesis -> Iterative Refinement -> Output Formatting.

## Key Principles

The framework rests on several evidence-based practices:

- **Context Clarification**: Regenerate input to prevent framing effects
- **Abstraction First**: Principles before specifics (+7-27% performance improvement from research)
- **Self-Generated Analogies**: Parametric knowledge access outperforms fixed examples
- **Factored Verification**: Independent checking achieves significant accuracy gains
- **Actionable Feedback**: Specific element-problem-action guidance beats generic critique

## Academic Foundation

Design incorporates research from ICLR, ACL, NAACL, ICML, and NeurIPS showing that explicit planning reduces errors from 12% to 3%, and complex reasoning chains improve outcomes by 5.3-18%.

## Output Adaptation

Final formatting adjusts based on question type:
- Taxonomies: include rationale and edge cases
- Trade-offs: specify balance points
- Definitional answers: map boundaries and adjacent concepts

## When to Use

- Taxonomy design questions
- Conceptual analysis with unknown structure
- Trade-off exploration across multiple dimensions
- Definitional questions requiring boundary mapping
- Any analytical question where the answer format is itself part of the answer
