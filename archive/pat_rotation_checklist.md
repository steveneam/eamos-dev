# GitHub PAT Rotation Checklist

## Files referencing GITHUB_PAT

| File | Line(s) | Contains token value? |
|---|---|---|
| `app/backend/.env` | 31 | **YES — rotate this token immediately** |
| `.env.example` | — | No placeholder line present — add one (see step 4) |
| `HANDOFF-session6.md` | 13, 40, 166 | Key name only, no value |
| `PROGRESS.md` | 112 | Key name only, no value |
| `CLAUDE.md` | 346 | Key name only, no value |

The token beginning `ghp_Dms...` on `.env` line 31 was exposed in a chat
session. It must be revoked and replaced before any use of the push scripts.

## Steps to rotate

### 1. Revoke the old token
- GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Find the token starting `ghp_Dms...` → click **Delete / Revoke**

### 2. Generate a new token
- GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Click **Generate new token (classic)**
- Name: `eamos-dev-push`
- Expiration: 90 days (or no expiration for local dev only)
- Scopes required: `repo` (full repository access — gives push access)
- Click **Generate token** — copy the value immediately, it is shown once

### 3. Update .env
Open `E:\eamos\app\backend\.env` and replace the
`GITHUB_PAT=` line with the new value:
```
GITHUB_PAT=<new token here>
```

### 4. Add placeholder to .env.example
Open `E:\eamos\app\backend\.env.example` and add:
```
# GitHub — push scripts
GITHUB_PAT=
```
This signals to collaborators that the variable is required without
committing a real value.

### 5. Confirm .gitignore coverage
- Root `E:\eamos\.gitignore` already lists `.env` — confirmed
- Backend folder has no separate `.gitignore`; the root rule covers it
- Never commit `.env` to any branch

## .env variable name
`GITHUB_PAT`
Set in: `E:\eamos\app\backend\.env`
Used by: push scripts that call the GitHub REST API directly (no git binary)
Minimum scope needed: `repo`
