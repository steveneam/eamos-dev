# routes/

HTTP route handlers. One file per resource group; each file is registered in `app/main.py`.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `auth.py` | Login, token refresh, user registration endpoints | Changing auth flow |
| `health.py` | Health-check endpoint (`GET /health`) | Checking startup or liveness probes |
| `lookup.py` | `POST /api/v1/lookup` — variant evidence pipeline entry point | Changing or debugging the lookup flow |
| `reports.py` | Patient report upload, retrieve, list endpoints | Changing or debugging patient report flow |
| `reviews.py` | Clinician review submission and retrieval | Changing review/sign-off flow |
| `runs.py` | Run creation, status, result retrieval | Changing or debugging the run lifecycle |
| `search.py` | Search indexing and query endpoints | Changing or debugging search |
