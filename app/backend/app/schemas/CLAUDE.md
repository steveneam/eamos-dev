# schemas/

Pydantic request and response models. One file per domain area. These are the API contract; active frontend TypeScript types in `app/web/lib/backend.ts` must match.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `auth.py` | Login request, token response models | Changing auth endpoints |
| `chat.py` | Chat message and session models | Changing chat/run-chat endpoints |
| `draft.py` | LLM draft generation request/response | Changing draft rendering |
| `lookup.py` | Variant lookup request and `ReportPayload` response | Changing the lookup endpoint contract |
| `report.py` | Patient report upload, full report response | Changing patient report endpoints |
| `run.py` | Run creation, status, and result models | Changing run lifecycle endpoints |
| `search.py` | Search query and result models | Changing search endpoints |
