# Eamos application

The product has two maintained application roots:

- `web/`: the sole frontend, built with Next.js, React, and TypeScript;
- `backend/`: the FastAPI service, schemas, providers, repositories, and tests.

The historical `frontend/` Vite application was retired on 2026-07-15. Its
useful pure tests now run from their corresponding `web/` modules, and Git
history preserves the old implementation.

## Contract ordering

Backend Pydantic models under `backend/app/schemas/` are authoritative. Update
them first, then update `web/lib/backend.ts` in the same change. The parity
canary is `backend/tests/test_frontend_contract.py`.

## Development

```bash
npm --prefix app/web run dev
cd app/backend && python -m uvicorn app.main:create_app --factory --reload
```

The web app defaults to `http://localhost:3000`; the backend defaults to
`http://localhost:8000/api/v1`.
