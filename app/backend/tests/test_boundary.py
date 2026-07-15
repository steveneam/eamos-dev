"""Structural boundary ratchets for the backend (executable wiring tracker).

These four pytest ratchets go red on cross-code drift. Each pins a boundary to a
frozen allowlist so a NEW violation fails the build while the existing
(tech-debt) exceptions do not, matching the ratchet philosophy in
docs/parallel-agents/ratchet-philosophy.md.

  1. Thin routes        - route modules import no NEW repository/database internals.
  2. Single env reader  - os.environ/os.getenv is read only in config.py plus an
                          enumerated exception set.
  3. LLM call-site pin  - AIGatewayEngine construction and its .complete/.stream_chat
                          /.embed calls stay within a frozen allowlist, so every LLM
                          call site is accounted for (the choke-point precondition).
  4. No conflict markers - no merge-conflict markers survive in tracked files.

This file is kept ruff-clean and black-clean so the residual format-conform sweep
(M-017) produces no diff on it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND_APP = ROOT / "app" / "backend" / "app"
ROUTES_DIR = BACKEND_APP / "api" / "routes"


def _py_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# ---------------------------------------------------------------------------
# 1. Thin routes: no NEW repository/database-internal imports in route modules.

ROUTE_DB_REPO_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+app\.(?:repos|core\.db)\b",
    re.MULTILINE,
)

# Routes that still import a repo/db internal today (tech debt, pending thinning
# behind a service). Frozen: a route NOT on this list may not add such an import.
ROUTE_DB_REPO_ALLOWLIST = {
    "app/backend/app/api/routes/health.py",
    "app/backend/app/api/routes/materialization.py",
    "app/backend/app/api/routes/variant_library.py",
}


def test_route_modules_do_not_add_repo_or_db_imports() -> None:
    offenders = []
    for path in ROUTES_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        if ROUTE_DB_REPO_IMPORT_RE.search(path.read_text(encoding="utf-8")):
            rel = _rel(path)
            if rel not in ROUTE_DB_REPO_ALLOWLIST:
                offenders.append(rel)

    assert not offenders, (
        "Route modules must stay thin - delegate to a service instead of importing "
        "app.repos.* / app.core.db directly. New offenders beyond the frozen "
        "allowlist: " + ", ".join(sorted(offenders))
    )


# ---------------------------------------------------------------------------
# 2. Single env reader: os.environ/os.getenv only in config.py + exceptions.

ENV_READ_RE = re.compile(r"\bos\.(?:environ|getenv)\b")

ENV_READ_ALLOWLIST = {
    "app/backend/app/core/config.py",
    "app/backend/app/core/sentry.py",
    "app/backend/app/cli/eamos_crispr_score_preflight.py",
}


def test_environment_is_read_only_in_config_and_exceptions() -> None:
    offenders = []
    for path in _py_files(BACKEND_APP):
        if ENV_READ_RE.search(path.read_text(encoding="utf-8")):
            rel = _rel(path)
            if rel not in ENV_READ_ALLOWLIST:
                offenders.append(rel)

    assert not offenders, (
        "os.environ / os.getenv must be read only in app/core/config.py (plus the "
        "enumerated exceptions). Move config reads into Settings. Offenders: "
        + ", ".join(sorted(offenders))
    )


# ---------------------------------------------------------------------------
# 3. LLM call-site inventory pinned to a frozen allowlist. Every AIGatewayEngine
#    construction and every .complete/.stream_chat/.embed call is accounted for,
#    so a new (potentially un-metered) LLM call site cannot slip in unreviewed.

LLM_CONSTRUCT_RE = re.compile(r"\bAIGatewayEngine\s*\(")
LLM_CALL_RE = re.compile(r"\.(?:complete|stream_chat|embed)\s*\(")

LLM_CONSTRUCT_ALLOWLIST = {
    "app/backend/app/agents/client.py",
    "app/backend/app/cli/eamos_literature_embed_materialize.py",
    "app/backend/app/services/ai_gateway/retrieval.py",
}

LLM_CALL_ALLOWLIST = {
    "app/backend/app/agents/client.py",
    "app/backend/app/services/ai_gateway/retrieval.py",
    "app/backend/app/services/ai_gateway/structured.py",
}


def test_llm_call_site_inventory_is_pinned() -> None:
    construct_offenders = []
    call_offenders = []
    for path in _py_files(BACKEND_APP):
        text = path.read_text(encoding="utf-8")
        rel = _rel(path)
        if LLM_CONSTRUCT_RE.search(text) and rel not in LLM_CONSTRUCT_ALLOWLIST:
            construct_offenders.append(rel)
        if LLM_CALL_RE.search(text) and rel not in LLM_CALL_ALLOWLIST:
            call_offenders.append(rel)

    assert not construct_offenders, (
        "New AIGatewayEngine construction outside the frozen allowlist - route it "
        "through the metered gateway path and update the allowlist deliberately: "
        + ", ".join(sorted(construct_offenders))
    )
    assert not call_offenders, (
        "New LLM call site (.complete/.stream_chat/.embed) outside the frozen "
        "allowlist - every LLM call must be accounted for: " + ", ".join(sorted(call_offenders))
    )


# ---------------------------------------------------------------------------
# 4. No merge-conflict markers in tracked files (CRLF-safe: exactly-7 markers
#    matched at line start with a whitespace/EOL boundary, so `=======\r` is
#    caught and a decorative `====...` run of 8+ is not). Markers are assembled
#    from fragments so this test file never contains a literal 7-char marker.


def test_no_merge_conflict_markers_in_tracked_files() -> None:
    boundary = "([[:space:]]|$)"
    patterns = []
    for marker in ("<" * 7, "=" * 7, ">" * 7):
        patterns += ["-e", "^" + marker + boundary]
    result = subprocess.run(
        ["git", "grep", "-I", "-n", "-E", *patterns],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        raise AssertionError("merge-conflict markers found in tracked files:\n" + result.stdout)
    assert (
        result.returncode == 1
    ), f"git grep failed (rc={result.returncode}): {result.stderr.strip()}"
