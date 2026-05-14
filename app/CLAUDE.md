# app/

Full-stack application: React/Vite frontend + FastAPI/Python backend + shared API contract.

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `frontend/` | React + TypeScript + Vite + Tailwind — variant lookup UI and patient report flow | Any frontend or UI work |
| `backend/` | FastAPI + Python — genomic pipeline, tools, rules engine, API routes | Any backend, API, or pipeline work |
| `shared/` | OpenAPI contract JSON, demo data fixtures | Changing API contract, checking type definitions |

## Development

```powershell
# Frontend dev server → http://localhost:5173
cd app/frontend
npm run dev      # node lives at C:\Program Files\nodejs\node.exe (system install, on PATH)

# Backend → http://localhost:8000
cd app/backend
python -m uvicorn app.main:create_app --factory --reload
```

API base URL (frontend → backend): `http://localhost:8000/api/v1`
Node.js: `C:\Program Files\nodejs\node.exe` (IT-managed system install, on PATH)
