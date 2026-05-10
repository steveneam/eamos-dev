# core/

Application infrastructure: configuration loading, database session, FastAPI dependency injection, and logging.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `config.py` | Settings class — reads `.env`, exposes `USE_REAL_APIS`, `LLM_PROVIDER`, `JWT_SECRET` | Adding or changing environment variables |
| `db.py` | SQLAlchemy engine and session factory | Changing database backend or connection config |
| `deps.py` | FastAPI `Depends()` wrappers: current user, DB session | Adding auth-gated endpoints, dependency changes |
| `logging.py` | Structured logging setup | Changing log format, level, or output |
