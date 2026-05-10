# Demo App Home

This is the **single home for the live demo app**.

We keep the demo split into:
- `backend/` — API, tool wrappers, rules, and draft-generation workflow
- `frontend/` — demo UI for case intake, draft review, and final output
- `shared/` — contracts and demo data used by both sides

## Folder layout

```text
04_demo/app/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── agents/
│   │   ├── tools/
│   │   ├── services/
│   │   ├── rules/
│   │   ├── schemas/
│   │   └── fixtures/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   ├── components/
│   │   ├── features/
│   │   ├── lib/
│   │   └── types/
│   └── public/
└── shared/
    ├── contracts/
    └── demo-data/
```

## Design rule

This app should stay **demo-first**:
- fake data is acceptable
- real workflow matters more than deep infrastructure
- one golden path first
- backend logic should stay thin and readable
- frontend should optimize for clarity in a 60–90 second demo

## Build rule

Start from:
1. `shared/contracts/`
2. `shared/demo-data/`
3. `backend/` contract-compatible endpoints
4. `frontend/` screens wired to those contracts

That keeps both sides aligned while disease/referral narrowing continues.
