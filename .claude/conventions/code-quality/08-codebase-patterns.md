<!-- Source: https://github.com/solatis/claude-config — integrated into Eamos project -->
<!-- applicable_phases: codebase_review, refactor_code -->

# Codebase Patterns

Evaluate patterns that only become visible across the entire codebase.

**The core question**: What patterns are emerging? Some issues are invisible at file scope but obvious when stepping back. Complex cross-file operations, repeated transformations that belong in shared abstractions, and dead exports cluttering the codebase -- these require whole-codebase visibility to detect.

**What to look for**:

- Operations requiring reading 5+ files to understand
- The same transformation repeated across 3+ files
- Exported symbols with zero consumers
- Feature flags that are always true or false

**The threshold**: Flag when cross-file complexity creates comprehension barriers. Flag when the same transformation in 3+ places signals a missing abstraction. These patterns become visible only after seeing multiple implementations -- they cannot be detected from individual files.

<design-mode>
Not applicable -- this group requires whole-codebase visibility to evaluate.
</design-mode>

<code-mode>
When evaluating actual code (Codebase Review, Refactor):

- Can I understand this operation by reading 2-3 files?
- Do repeated transformations signal a missing abstraction?
- Are there exported symbols with no consumers?
- Are feature flags stuck in one state?

Evidence format: Quote code from multiple files showing the pattern, with file:line references.
</code-mode>

---

## 1. Cross-File Comprehension

<principle>
Operations should be understandable without reading five or more files. When understanding a single operation requires assembling context from many scattered locations, the boundaries are wrong.
</principle>

Detect: How many files must I read to understand this operation completely? Are there implicit contracts between files that lack documentation?

<grep-hints>
Structural indicators (starting points, not definitive):
Call chains, event handler registration, implicit dependencies between modules
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Comprehension barriers

- Understanding a single operation requires reading 5+ files
- Implicit contracts between files (undocumented assumptions about order, state, or format)
- Any cross-file pattern requiring reconstruction from scattered sources

[medium] Hidden dependencies

- Cross-module side effects (module A's behavior changes based on module B's state)
- Undocumented initialization order requirements
</violations>

<exceptions>
Framework-enforced patterns where the framework documents the contract. Plugin architectures with clear extension points.
</exceptions>

<threshold>
Flag when understanding a single operation requires reading 5+ files with no documentation explaining the contract.
</threshold>

## 2. Abstraction Opportunities

<principle>
Repeated transformations signal missing concepts. When the same operation appears in 3+ files, the operation belongs in a shared abstraction.
</principle>

Detect: Is the same transformation repeated across multiple files? Would extracting it create a reusable concept with a clear name?

<grep-hints>
Structural indicators (starting points, not definitive):
Parallel implementations with similar structure, repeated data transformation patterns
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Missing abstractions

- Same transformation applied in multiple files (3+ occurrences)
- Parallel implementations with identical structure and different variable names
- Any repeated pattern that would benefit from a named abstraction

[medium] Partial abstraction

- Abstraction exists but is inconsistently used (some callers use it, others duplicate logic)
</violations>

<exceptions>
Intentional duplication for isolation. Domain-specific variations that look similar but serve different concepts.
</exceptions>

<threshold>
Flag when the same transformation appears 3+ files AND extracting it would create a reusable concept with a clear name.
</threshold>

## 3. Zombie Code (Codebase Scope)

<principle>
Dead exports are noise at scale. Exported symbols with no consumers, and feature flags that never toggle, clutter the codebase and mislead maintainers about what is actually used.
</principle>

Detect: Are there exported symbols that have zero callers anywhere in the codebase? Are there feature flags that are always in one state?

<grep-hints>
Structural indicators (starting points, not definitive):
Exported symbols, feature flag evaluations, public API surface
</grep-hints>

<violations>
Illustrative patterns (not exhaustive -- similar violations exist):

[high] Dead exports

- Exported functions with 0 callers anywhere in codebase
- Feature flags always true/false (never toggled in any environment)
- Any exported symbol that serves no active consumer

[medium] Orphaned modules

- Entire modules with no importers
- Dead configuration options never read by any code path
</violations>

<exceptions>
Public API entry points (user-facing interfaces). Plugin interfaces (external consumers). Documented compatibility shims. Test helpers used only in test files.
</exceptions>

<threshold>
Flag when exported symbol has 0 callers in the codebase AND is not a public API, plugin interface, or documented compatibility shim.
</threshold>
