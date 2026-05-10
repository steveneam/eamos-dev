# tests/

pytest test suite for the FastAPI backend. Mix of unit, API, and integration tests.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `conftest.py` | pytest fixtures — test client, DB session, auth helpers | Adding tests, debugging test setup |
| `test_auth_api.py` | Auth endpoint tests | Changing auth routes or logic |
| `test_docker_integration.py` | Docker integration test — full stack smoke test | Testing containerised deployment |
| `test_draft_render.py` | Draft rendering unit tests | Changing LLM draft generation |
| `test_real_agent_smoke.py` | Smoke test against real APIs — requires `USE_REAL_APIS=true` | Testing live API connectivity |
| `test_report_api.py` | Patient report endpoint tests | Changing patient report routes |
| `test_review_api.py` | Review endpoint tests | Changing review routes |
| `test_run_chat_api.py` | Run-chat endpoint tests | Changing run-chat routes |
| `test_run_flow.py` | End-to-end run flow tests | Changing pipeline orchestration |
| `test_search_api.py` | Search endpoint tests | Changing search routes |
