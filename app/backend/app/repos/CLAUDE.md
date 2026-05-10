# repos/

SQLite data-access layer. One repository file per domain entity.

## Files

| File | What | When to read |
| ---- | ---- | ------------ |
| `reports_repo.py` | CRUD for patient reports | Changing or debugging report persistence |
| `run_repo.py` | CRUD for pipeline runs | Changing or debugging run persistence |
| `search_repo.py` | Search index read/write | Changing or debugging search persistence |
| `users_repo.py` | CRUD for user accounts | Changing or debugging user persistence |
