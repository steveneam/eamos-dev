<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
# Decision Critic

Adversarial decision analysis skill. LLMs are sycophants -- they agree with you and validate your reasoning. This skill stress-tests decisions instead.

## Overview

The skill combats agreement bias through structured adversarial analysis. Rather than validating decisions conversationally, it uses chain-of-verification, self-consistency checking, and multi-expert prompting to generate genuine criticism.

## Four-Phase Process

1. **Decomposition** -- Extract specific claims and assumptions from the decision
2. **Verification** -- Independently answer questions without anchoring on the decision
3. **Challenge** -- Explore counterarguments and failure modes
4. **Synthesis** -- Reach a verdict based on evidence, not intuition

## When to Use

- Technology selection (database, framework, architecture)
- Performance vs. maintainability trade-offs
- Decisions you are uncertain about
- Any consequential choice where sycophantic validation is a risk

## Anti-Sycophancy Mechanisms

Three mechanisms prevent automatic validation:

- **Chain-of-verification**: Separates verification into independent steps
- **Self-consistency**: Identifies reasoning contradictions
- **Multi-expert prompting**: Incorporates diverse viewpoints

## Example

When evaluating Redis vs PostgreSQL for sessions, the skill:
1. Identifies specific claims (speed differences)
2. Tests assumptions (durability requirements)
3. Stress-tests against scenarios (shopping cart persistence under failure)
4. Synthesizes evidence into a verdict
