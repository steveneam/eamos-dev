<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
<!-- applicable_phases: diff_review, codebase_review, refactor_code -->

# Repetition & Consistency

Evaluate whether code is DRY and internally consistent.

**The core question**: Is this DRY and consistent? Repetition creates maintenance burden -- when business rules change, all copies must be updated. Inconsistency within a class creates confusion about which approach is correct. Both patterns indicate missing abstractions.

**What to look for**:

- Duplicated logic that could be extracted
- Validation scattered across layers
- Business rules duplicated without a single authoritative source
- Repeated condition patterns signaling missing abstraction
- Inconsistent error handling within the same class or module

**The threshold**: Flag when duplication creates real maintenance risk (two+ places must be updated together). Flag when inconsistency within a class creates confusion. Style variations without behavioral impact are not DRY violations.

<design-mode>
Not applicable -- this group requires actual code to evaluate patterns.
</design-mode>

<code-mode>
When evaluating actual code (Diff Review, Codebase Review, Refactor):

- Is the same logic duplicated in multiple places?
- Are business rules scattered across layers?
- Do repeated condition patterns signal a missing abstraction?
- Is error handling consistent within this class?

Evidence format: Quote code from multiple locations showing the pattern.
</code-mode>

---

## 1. Duplication

<principle>
Logic that must change together must live together. When the same logic appears in multiple places, a change to the logic requires hunting down all copies.
</principle>

Detect: If the business requirement behind this logic changed, how many places would I need to update?

<grep-hints>
Pattern indicators (starting points, not definitive):
Near-identical function bodies, copy-pasted blocks, parallel function pairs
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Coupled duplication

- Copy-pasted logic blocks that must change together
- Parallel functions with near-identical bodies
- Any duplication where a requirement change demands multiple edits

[medium] Structural repetition

- Repeated try/catch patterns (extract to utility)
- Boilerplate repeated across similar operations

[low] Minor repetition

- Simple value repetition (extract to constant)
</violations>

<exceptions>
Coincidental duplication (code that looks similar but would diverge on requirement change). Intentional parallel structure for readability. Generated code.
</exceptions>

<threshold>
Flag when 2+ code blocks would both require changes for a single requirement change. Coincidental similarity is not a violation.
</threshold>

## 2. Validation Scattering

<principle>
Validation for a concept should live at one authoritative location. When the same input is validated in multiple places, inconsistencies accumulate over time.
</principle>

Detect: How many places validate this input? If the validation rule changes, how many locations must be updated?

<grep-hints>
Pattern indicators (starting points, not definitive):
`if.*is None`, `if.*== ""`, `if len(.*) ==`, similar validation checks in multiple locations
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Scattered validation

- Same input validated in multiple layers (controller, service, repository)
- Any validation rule that must be updated in multiple locations

[medium] Partial validation

- Validation without error context (no indication of which field failed)
- Validation in wrong layer (business rule in infrastructure layer)

[low] Redundant checks

- Null checks for values already guaranteed non-null by caller contract
</violations>

<exceptions>
Security-critical validation at multiple layers (defense in depth). Contract assertions in debug builds.
</exceptions>

<threshold>
Flag when the same validation logic appears in 2+ places AND the rule could change independently.
</threshold>

## 3. Business Rule Scattering

<principle>
Business rules should have a single authoritative source. When the same rule is implemented in multiple places, they drift apart as requirements evolve.
</principle>

Detect: Is this business rule implemented in multiple places? If the rule changes, how many files must be updated?

<grep-hints>
Pattern indicators (starting points, not definitive):
Domain-specific constants used in multiple places, pricing/discount calculations, access control checks
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Rule fragmentation

- Business logic duplicated across services/modules
- Domain rules expressed as raw conditions in multiple places
- Any rule that must be updated in multiple locations when requirements change

[medium] Implicit rules

- Business logic in data access layer
- Domain concepts expressed only through primitive comparisons in 2+ files
</violations>

<exceptions>
Rules legitimately different per context. Intentional denormalization with documented sync strategy.
</exceptions>

<threshold>
Flag when same business rule appears in 2+ files AND would require coordinated updates on rule change.
</threshold>

## 4. Condition Pattern Repetition

<principle>
When the same condition pattern appears multiple times, it signals a missing abstraction. Repeated patterns should be named and extracted.
</principle>

Detect: Does this condition pattern appear elsewhere? If the condition logic changes, how many places must be updated?

<grep-hints>
Pattern indicators (starting points, not definitive):
Same multi-clause condition appearing in different functions, repeated role/permission checks
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Repeated predicates

- Same multi-clause condition appearing 3+ times
- Repeated permission/role checks without extraction

[medium] Pattern repetition

- Same condition structure with minor variable substitution (extract parameterized predicate)
</violations>

<exceptions>
Simple single-condition checks. Conditions that look similar but represent different business concepts.
</exceptions>

<threshold>
Flag when the same condition pattern appears 3+ times AND would benefit from extraction.
</threshold>

## 5. Error Pattern Consistency (File Scope)

<principle>
Error handling within a class should be consistent. Mixed approaches -- some methods throwing, others returning codes -- confuse callers about what to expect.
</principle>

Detect: Is error handling consistent within this class/module? Would a caller know what to expect from similar operations?

<grep-hints>
Pattern indicators (starting points, not definitive):
Mixed `raise`/`return None`/`return False` patterns, inconsistent error types within same class
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Inconsistent strategy

- Methods in same class mixing exceptions and return codes
- Same error condition handled differently in similar methods

[medium] Pattern drift

- Inconsistent error message formats within module
- Some methods wrap errors, others propagate raw
</violations>

<exceptions>
Different patterns for different abstraction levels within same file. Intentional mixed strategy with clear documentation.
</exceptions>

<threshold>
Flag when the same class uses 2+ incompatible error strategies AND no clear rule distinguishes when each applies.
</threshold>
