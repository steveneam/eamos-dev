# Demo Plan

## App location

The live demo app should live in:

- `04_demo/app/backend`
- `04_demo/app/frontend`
- `04_demo/app/shared`

This keeps the demo implementation isolated from the planning docs while still sitting inside the `04_demo` workspace.

## Recommended structure

```text
04_demo/
├── demo-plan.md
└── app/
    ├── backend/
    │   ├── app/api/routes/
    │   ├── app/agents/
    │   ├── app/tools/
    │   ├── app/services/
    │   ├── app/rules/
    │   ├── app/schemas/
    │   ├── app/fixtures/
    │   └── tests/
    ├── frontend/
    │   ├── src/routes/
    │   ├── src/components/
    │   ├── src/features/
    │   ├── src/lib/
    │   ├── src/types/
    │   └── public/
    └── shared/
        ├── contracts/
        └── demo-data/
```

## Primary demo path

1. Upload a genetic/genomic report PDF
2. Review extracted structured fields
3. Run backend interpretation flow
4. Show recommendation + evidence + uncertainty
5. Reviewer edits one field
6. Export final review-ready output

## What lives where

### Backend
- thin FastAPI API
- report upload + extraction flow
- thin LangChain layer for extraction and draft wording
- tool wrappers for Franklin / VEP / SpliceAI / ClinVar
- deterministic decision rules
- draft rendering

### Frontend
- report upload screen
- extracted-data review screen
- evidence/recommendation screen
- clinician review screen
- export/final output screen

### Shared
- canonical request/response contracts
- sample cases
- expected outputs for the golden-path demo

Backend should consume shared contracts from here rather than duplicating schema snapshots inside backend fixtures.

## Demo scenario checklist

- Scenario must be specific (one disease context)
- Must include at least one "missing field" branch
- Must show human-review decision point clearly
- Must have an offline or fixture-backed fallback path

## Risks to avoid in front of judges

- vague / overbroad claim
- overcomplicated UX
- invisible confidence / uncertainty handling
- backend overengineering before the golden path works

## Failure fallback

- If a live API step is delayed, use pre-loaded fixture responses
- Never break flow with empty state
- Always keep fallback content visible and believable
