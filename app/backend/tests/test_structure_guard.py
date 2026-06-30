from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY

ROOT = Path(__file__).resolve().parents[3]

ROUTE_DECORATOR_RE = re.compile(
    r"^\s*@app\.(get|post|put|patch|delete|options|head)\(",
    re.MULTILINE,
)
STATIC_IMPORT_RE = re.compile(
    r"""^\s*import\s+(?:type\s+)?(?:(?:[\w*{}\s,]+)\s+from\s+)?["']([^"']+)["']""",
)

FRONTEND_LIB_ROOTS = (
    ROOT / "app" / "web" / "lib",
    ROOT / "app" / "frontend" / "src" / "lib",
)

FRONTEND_TS_ROOTS = (
    ROOT / "app" / "web",
    ROOT / "app" / "frontend" / "src",
)

SOURCE_ASSET_ROOT = ROOT / "app" / "backend" / "data" / "source_assets"

ACTIVE_FRONTEND_SOURCE_OF_TRUTH_DOCS = (
    ROOT / "README.md",
    ROOT / "CODEX.md",
    ROOT / "AGENTS.md",
    ROOT / "plans" / "README.md",
    ROOT / "plans" / "frontend-rebuild.md",
    ROOT / "plans" / "v2-frontend.md",
    ROOT / "docs" / "repo-structure" / "plan.md",
    ROOT / "docs" / "repo-structure" / "audit-2026-06-30.md",
    ROOT / "docs" / "search-index" / "spec.md",
    ROOT / "docs" / "search-index" / "plan.md",
)

HEAVY_BROWSER_PACKAGES = {
    "@react-three/drei",
    "@react-three/fiber",
    "echarts",
    "lottie-web",
    "monaco-editor",
    "molstar",
    "ngl",
    "pdfjs-dist",
    "plotly.js",
    "plotly.js-dist",
    "plotly.js-dist-min",
    "three",
}

# Tripwires for known oversized files. These are not repo-wide line caps; they
# keep current hotspots from growing further without a deliberate split.
HOTSPOT_LINE_BUDGETS = {
    "app/backend/app/services/gene_viewer.py": 3600,
    "app/backend/app/services/pubmed_local.py": 3100,
    "app/backend/app/services/lookup_service.py": 3000,
    "app/backend/app/services/workbench_design.py": 2300,
    "app/backend/app/services/clinvar_local.py": 2200,
    "app/backend/app/services/protein_annotation.py": 1000,
    "app/web/components/workbench/workbench.css": 4100,
    "app/web/components/report/ReportGeneViewer.tsx": 2600,
    "app/web/components/report/PopulationFrequencySection.tsx": 1950,
    "app/web/components/report/ReportClient.tsx": 1850,
    "app/web/components/compare/CompareClient.tsx": 1400,
}

LIVE_VITE_DOC_PATTERNS = (
    re.compile(r"\bReact/Vite frontend\b", re.IGNORECASE),
    re.compile(r"\bReact/Vite\b.*\bdo NOT migrate to Next", re.IGNORECASE),
    re.compile(r"\bcd\s+app/frontend\b", re.IGNORECASE),
    re.compile(r"\bapp/frontend/src/lib/backend\.ts\b", re.IGNORECASE),
    re.compile(r"\bFrontend\s*=\s*`app/frontend/`", re.IGNORECASE),
)

FROZEN_DOC_MARKERS = (
    "superseded historical plan",
    "frozen vite frontend reference",
    "frozen historical vite reference",
    "historical/reference frontend",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8"))


def _iter_source_files(root: Path, suffixes: tuple[str, ...]):
    if not root.exists():
        return
    excluded = {"node_modules", ".next", "dist", "build", "coverage", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in excluded for part in path.parts):
            continue
        yield path


def _iter_active_doc_files():
    for path in ACTIVE_FRONTEND_SOURCE_OF_TRUTH_DOCS:
        if path.exists():
            yield path


def _tracked_source_asset_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "app/backend/data/source_assets"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line.strip() for line in result.stdout.splitlines() if line.strip()]


def _package_name(specifier: str) -> str:
    if specifier.startswith("@"):
        parts = specifier.split("/")
        return "/".join(parts[:2])
    return specifier.split("/", 1)[0]


def test_backend_entrypoint_only_wires_routes() -> None:
    main_py = ROOT / "app" / "backend" / "app" / "main.py"
    text = _read(main_py)

    assert not ROUTE_DECORATOR_RE.search(text), (
        "FastAPI handlers belong in app/backend/app/api/routes/<domain>.py, " "not in main.py."
    )
    assert "build_api_router" in text
    assert "app.include_router(build_api_router())" in text


def test_backend_route_modules_use_api_router() -> None:
    route_dir = ROOT / "app" / "backend" / "app" / "api" / "routes"
    offenders: list[str] = []
    for path in route_dir.glob("*.py"):
        if path.name == "__init__.py":
            continue
        text = _read(path)
        if "APIRouter" not in text or not re.search(r"\brouter\s*=\s*APIRouter\(", text):
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, "Route modules must expose `router = APIRouter(...)`: " + ", ".join(
        offenders
    )


def test_frontend_libs_do_not_add_barrels_or_flat_feature_api_modules() -> None:
    offenders: list[str] = []
    for root in FRONTEND_LIB_ROOTS:
        offenders.extend(str(path.relative_to(ROOT)) for path in root.rglob("index.ts"))
        offenders.extend(str(path.relative_to(ROOT)) for path in root.rglob("index.tsx"))
        offenders.extend(str(path.relative_to(ROOT)) for path in root.glob("*-api.ts"))
        offenders.extend(str(path.relative_to(ROOT)) for path in root.glob("*-api.tsx"))

    assert not offenders, (
        "Frontend lib modules should import concrete files directly. "
        "Use lib/<feature>/api.ts for feature endpoints and avoid barrels: "
        + ", ".join(sorted(offenders))
    )


def test_active_docs_do_not_point_to_vite_as_live_frontend() -> None:
    offenders: list[str] = []
    for path in _iter_active_doc_files():
        text = _read(path)
        first_lines = "\n".join(text.splitlines()[:20]).lower()
        is_frozen_context = any(marker in first_lines for marker in FROZEN_DOC_MARKERS)
        if is_frozen_context:
            continue
        for pattern in LIVE_VITE_DOC_PATTERNS:
            if pattern.search(text):
                offenders.append(str(path.relative_to(ROOT)))
                break

    assert not offenders, (
        "Active docs must point frontend product work at app/web. "
        "Mark old Vite docs as superseded/frozen before mentioning live "
        "app/frontend workflows: " + ", ".join(sorted(offenders))
    )


def test_tracked_source_assets_are_manifest_backed_registered_assets() -> None:
    offenders: list[str] = []
    for path in _tracked_source_asset_files():
        relative = path.relative_to(SOURCE_ASSET_ROOT)
        parts = relative.parts
        if not parts:
            continue
        source_id = parts[0]
        if not DEFAULT_DATA_SOURCE_REGISTRY.has(source_id):
            offenders.append(f"{path.relative_to(ROOT)}: unregistered source id {source_id}")
            continue
        if path.name.endswith(".manifest.json"):
            continue
        manifest_path = Path(f"{path}.manifest.json")
        if not manifest_path.exists():
            offenders.append(f"{path.relative_to(ROOT)}: missing manifest sidecar")

    assert not offenders, (
        "Tracked source assets must stay under a registered source id and every "
        "payload/checksum file must have a .manifest.json sidecar per "
        "docs/repo-structure/source-asset-policy.md: " + "; ".join(offenders)
    )


def test_heavy_browser_libraries_are_not_static_imports() -> None:
    offenders: list[str] = []
    for root in FRONTEND_TS_ROOTS:
        for path in _iter_source_files(root, (".ts", ".tsx")):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = STATIC_IMPORT_RE.match(line)
                if not match:
                    continue
                package = _package_name(match.group(1))
                if package in HEAVY_BROWSER_PACKAGES:
                    offenders.append(f"{path.relative_to(ROOT)}:{line_number}:{package}")

    assert (
        not offenders
    ), "Heavy browser libraries must be lazy/dynamic imports from browser-only code: " + ", ".join(
        offenders
    )


def test_known_hotspots_do_not_grow_without_a_split() -> None:
    offenders: list[str] = []
    for relative_path, budget in HOTSPOT_LINE_BUDGETS.items():
        path = ROOT / relative_path
        count = _line_count(path)
        if count > budget:
            offenders.append(f"{relative_path} has {count} lines, budget {budget}")

    assert not offenders, (
        "Known oversized files grew. Split by responsibility or update "
        "docs/repo-structure/plan.md with a deliberate new budget: " + "; ".join(offenders)
    )
