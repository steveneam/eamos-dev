# TIDER, Lindel, and Trace Decomposition Spec

## Status

Draft for review. This phase is specification only. It must not change runtime
behavior for the existing observed-only CRISPR TIDE route.

## Context

The Workbench now has a source-backed observed-only CRISPR outcomes path. The
current backend intentionally exposes a TIDE-like result surface without copying
or embedding the NKI TIDE solver, ICE, DECODR, Lindel, TIDER, or a public web
decomposition service. That behavior should remain stable until a validated
trace-decomposition implementation is added behind an explicit provider label.

This spec defines the next implementation lane for trace-level decomposition,
Lindel prediction, and TIDER-style template-directed repair analysis.

## Goals

- Add a local, source-backed trace-decomposition engine for edited Sanger AB1
  traces and matched controls.
- Keep observed indel decomposition, predicted Lindel repair distributions, and
  TIDER template-directed repair analysis as separate provider surfaces.
- Preserve the current observed-only TIDE route behavior until the new engine
  passes quality gates and contract tests.
- Fail closed for missing indexes, missing dependencies, low-quality traces, or
  unsupported analysis modes.
- Preserve explicit provenance, provider labels, warnings, and preflight state
  so commercialization and launch gating can be decided later.

## Non-Goals

- No copied external web engine code.
- No request-time calls to public TIDE, ICE, DECODR, Lindel, or TIDER sites.
- No Render, provider flip, Supabase, startup-download, or deployment changes in
  this phase.
- No UI changes until the backend response contract is reviewed.
- No claimed p-values, template repair fractions, or predicted bins unless the
  corresponding provider actually produced them and quality checks passed.

## Existing Boundaries

- `app/backend/app/services/trace_parser.py` is the bounded AB1 parsing layer.
- `app/backend/app/services/crispr_tide.py` is the current observed-only,
  consensus-based result path.
- `app/backend/app/schemas/workbench.py` owns the public Workbench response
  models.
- CRISPR guide scoring already treats Lindel as an optional predictor, separate
  from observed editing outcomes.

The new implementation should add an engine next to these modules instead of
mutating the observed-only service into a broader solver.

## Proposed Backend Shape

Add a new service module:

```text
app/backend/app/services/crispr_trace_decomposition.py
```

Core interfaces:

```python
class TraceDecompositionProvider(Protocol):
    def analyze(self, request: TraceDecompositionRequest) -> TraceDecompositionResult:
        ...

class LindelOutcomeProvider(Protocol):
    def predict(self, request: LindelOutcomeRequest) -> LindelOutcomeResult:
        ...

class TiderRepairProvider(Protocol):
    def analyze(self, request: TiderRepairRequest) -> TiderRepairResult:
        ...
```

The implementation should reuse parsed AB1 data from `trace_parser.py`, then
construct a bounded signal window around the cut site. The trace solver should
operate on channel intensities and peak positions when available, not only the
called consensus string.

Recommended route strategy:

- Prefer a new additive route, such as
  `POST /api/v1/crispr/trace-decomposition`, for the first validated engine.
- Keep `POST /api/v1/crispr/tide` stable and observed-only until the frontend
  TypeScript contract and disclosure copy are updated.
- If the existing route is extended later, use explicit `provider_mode` and
  additive nullable fields rather than changing current field semantics.

## Analysis Modes

### Observed Indel Decomposition

Inputs:

- Edited trace AB1.
- Matched control trace AB1.
- Reference context or guide/cut-site metadata sufficient to build the
  decomposition window.

Required outputs:

- `provider_label`
- `provider_mode = "observed_decomposition"`
- editing efficiency
- indel-size spectrum
- fit quality metrics
- trace quality metrics
- warnings
- notes
- `predicted_available = false`
- no Lindel or TIDER fields unless those providers also ran successfully

Implementation direction:

- Build candidate indel basis traces for bounded insertions and deletions around
  the cut site.
- Fit candidate basis weights with non-negative least squares or an equivalent
  constrained local solver.
- Normalize weights only after rejecting low-fit or low-quality windows.
- Report residual error and confidence/quality summaries, not unsupported
  statistical claims.

### Lindel Prediction

Inputs:

- Guide and target context.
- Optional existing CRISPR score preflight state and configured local Lindel
  environment.

Required outputs:

- `provider_mode = "lindel_prediction"`
- predicted repair-bin distribution
- frameshift probability when available
- dependency and model provenance
- warnings on unavailable model/runtime

Rules:

- Do not mix predicted Lindel bins into observed decomposition frequencies.
- Do not mark observed decomposition as predicted just because Lindel ran.
- If the Lindel runtime is not configured, return structured unavailability
  rather than mock predictions.

### TIDER-Style Template Repair

Inputs:

- Edited trace AB1.
- Control trace AB1.
- Donor or repair-template sequence.
- Cut-site and window metadata.

Required outputs:

- `provider_mode = "template_repair_decomposition"`
- template-directed repair estimate when supported
- indel spectrum
- fit metrics
- quality metrics
- warnings
- method notes describing limits of the local implementation

Rules:

- Require a donor/template input for TIDER mode.
- Fail closed when donor alignment is ambiguous.
- Do not report p-values unless the implementation explicitly computes and
  validates them against fixtures.

## Quality Gates

The provider must return a structured not-ready or failed status when any of
these checks fail:

- AB1 parsing fails or trace channels are unavailable.
- Edited/control trace windows cannot be aligned.
- Cut-site window falls outside the parsed trace.
- Signal-to-noise or average quality in the analysis window is below threshold.
- Residual fit is above threshold.
- Candidate basis is underdetermined for the requested indel range.
- Required provider dependency is missing.
- Provider preflight reports not-ready.

Responses must not expose raw local paths, secrets, full command lines with
private directories, or public-web fallback URLs.

## Preflight and Health Contract

Add a compact preflight surface before enabling runtime use:

- AB1 parser readiness.
- Optional numerical solver readiness.
- Optional Lindel runtime readiness.
- Optional TIDER/decomposition provider readiness.
- Fixture/golden-trace availability.
- Provider mode availability: auto, observed-only, forced decomposition,
  forced Lindel, forced TIDER.

Forced modes must fail closed when their provider is unavailable. Auto mode may
fall back to the existing observed-only response only when the response clearly
labels the fallback provider and includes a warning.

## Tests

Required before implementation is considered complete:

- Unit tests for AB1 parser error boundaries and low-quality trace rejection.
- Synthetic trace tests with known deletion, insertion, and mixed indel weights.
- Golden AB1 fixture tests for edited/control trace decomposition.
- Forced-mode fail-closed route tests.
- Auto-mode fallback tests that preserve provider labels and warnings.
- Lindel unavailable tests that return structured not-ready state.
- TIDER missing-donor and ambiguous-donor tests.
- Serialization tests proving response JSON contains no raw local paths.
- Frontend contract tests only after the backend route shape is accepted.

## Open Decisions

- Whether the first public contract should be a new
  `/crispr/trace-decomposition` route or an extension to `/crispr/tide`.
- Whether to depend on an existing numerical package already available in the
  backend environment or add a new pinned dependency.
- What AB1 golden fixtures can be committed or generated without licensing or
  patient-data risk.
- Whether TIDER-style template repair should ship after observed decomposition
  and Lindel prediction, rather than in the first runtime milestone.

## Implementation Order

1. Add response/request models behind a new route or explicitly reviewed route
   extension.
2. Add provider preflight and health status without enabling runtime use.
3. Add synthetic decomposition tests and local solver.
4. Add golden AB1 fixture tests.
5. Add forced-mode fail-closed behavior.
6. Add auto-mode fallback to the current observed-only provider with explicit
   fallback warnings.
7. Add Lindel prediction provider integration only after its local runtime
   preflight is reliable.
8. Add TIDER-style donor/template repair only after donor alignment and quality
   gates are tested.
