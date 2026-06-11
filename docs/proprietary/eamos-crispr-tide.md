# Eamos Observed-Only CRISPR TIDE Analyzer

Status: Active backend prototype
Type: Trace-analysis algorithm + CLI
Owner: Codex
Added: 2026-06-12 01:02 +1000 - Codex
Last updated: 2026-06-12 01:02 +1000 - Codex

## What It Does

Runs a local, observed-only TIDE-style comparison over two parsed AB1 Sanger
traces. It reports editing efficiency, a fit proxy, and an indel-size spectrum
through the shared `CrisprTideResponse` contract used by the Workbench
`/api/v1/crispr/tide` route.

The operator CLI is:

```powershell
python -m app.cli.eamos_crispr_tide --control control.ab1 --edited edited.ab1 --cut-site-index 100
```

## Why It Is Eamos-Original

The implementation deliberately does not embed the NKI TIDE solver, ICE, DECODR,
Lindel, or a copied external decomposition engine. It reuses Eamos' bounded AB1
parser, computes a transparent consensus-window indel estimate, and preserves
guardrail metadata so the product can distinguish observed trace evidence from
predicted repair models.

## Source Of Truth

- `app/backend/app/services/crispr_tide.py`
- `app/backend/app/services/trace_parser.py`
- `app/backend/app/api/routes/workbench.py`
- `app/backend/app/cli/eamos_crispr_tide.py`
- `app/backend/tests/test_workbench_api.py`
- `app/backend/tests/test_crispr_tide_cli.py`

## Caveats

- Observed-only: no Lindel, TIDER, p-values, or predicted repair distribution.
- AB1 parsing depends on Biopython.
- The CLI uses local file inputs and emits sanitized JSON summaries; it does not
  upload traces, call the network, or require the FastAPI server.
- A future signal-level engine such as Tracy would be a separate, explicitly
  reviewed provider path.
