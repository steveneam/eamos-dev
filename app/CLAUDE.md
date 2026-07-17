# app/

Full-stack application: Next.js/React frontend + FastAPI/Python backend.

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
| `web/` | **Next.js 16 (App Router) — the ACTIVE frontend.** Migrated surfaces (`/`, `/report`, `/workbench`, `/compare`, account/auth/legal). All current FE work lands here. | Any frontend or UI work |
| `backend/` | FastAPI + Python — genomic pipeline, tools, rules engine, API routes | Any backend, API, or pipeline work |

## Development

```powershell
# ACTIVE frontend (Next.js 16) — migrated surfaces
npm --prefix app/web run dev        # → http://localhost:3532

# node lives at C:\Program Files\nodejs\node.exe (system install, on PATH)

# Backend → http://localhost:8532
cd app/backend
python -m uvicorn app.main:create_app --factory --reload --port 8532
```

API base URL (frontend → backend): `http://localhost:8532/api/v1`
Node.js: `C:\Program Files\nodejs\node.exe` (IT-managed system install, on PATH)
