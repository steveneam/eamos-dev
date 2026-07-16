from __future__ import annotations

import json
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

FRONTEND_LIB_ROOTS = (ROOT / "app" / "web" / "lib",)

FRONTEND_TS_ROOTS = (ROOT / "app" / "web",)

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
    "app/backend/app/data_sources/registry.py": 30,
    "app/backend/app/data_sources/registry_models.py": 375,
    "app/backend/app/data_sources/registry_records.py": 1375,
    "app/backend/app/services/gene_viewer.py": 500,
    "app/backend/app/services/gene_viewer_full_locus.py": 850,
    "app/backend/app/services/gene_viewer_protein_tracks.py": 375,
    "app/backend/app/services/gene_viewer_source_client.py": 850,
    "app/backend/app/services/gene_viewer_source_provider.py": 575,
    "app/backend/app/services/gene_viewer_window.py": 500,
    "app/backend/app/services/pubmed_local.py": 1550,
    "app/backend/app/services/pubmed_local_constants.py": 160,
    "app/backend/app/services/pubmed_local_license_policy.py": 75,
    "app/backend/app/services/pubmed_local_models.py": 275,
    "app/backend/app/services/pubmed_local_parsing.py": 1250,
    "app/backend/app/services/lookup_service.py": 1750,
    "app/backend/app/services/lookup_service_cache.py": 425,
    "app/backend/app/services/lookup_service_clinvar_distribution.py": 100,
    "app/backend/app/services/lookup_service_publications_trials.py": 500,
    "app/backend/app/services/lookup_service_report_payload.py": 550,
    "app/backend/app/services/lookup_service_source_cache.py": 275,
    "app/backend/app/services/lookup_service_utils.py": 50,
    "app/backend/app/services/workbench_design.py": 300,
    "app/backend/app/services/workbench_design_alignment.py": 650,
    "app/backend/app/services/workbench_design_common.py": 100,
    "app/backend/app/services/workbench_design_fixture.py": 100,
    "app/backend/app/services/workbench_design_primer.py": 1150,
    "app/backend/app/services/workbench_design_protocols.py": 75,
    "app/backend/app/services/workbench_design_service.py": 750,
    "app/backend/app/services/clinvar_local.py": 2200,
    "app/backend/app/services/protein_annotation.py": 1000,
    "app/backend/app/services/variant_report_orchestrator.py": 900,
    "app/backend/app/services/variant_report_helpers.py": 275,
    "app/backend/app/services/variant_report_signals.py": 375,
    "app/web/components/workbench/workbench-designers.css": 900,
    "app/web/components/workbench/workbench-shell.css": 175,
    "app/web/components/workbench/workbench-side-panel.css": 550,
    "app/web/components/workbench/workbench-tools.css": 1025,
    "app/web/components/workbench/workbench-viewer.css": 1100,
    "app/web/components/report/ReportGeneViewer.tsx": 900,
    "app/web/components/report/gene-viewer/ReportProteinView.tsx": 750,
    "app/web/components/report/gene-viewer/geneViewerPresentation.tsx": 175,
    "app/web/components/report/gene-viewer/proteinViewModel.ts": 600,
    "app/web/components/report/gene-viewer/reportGeneViewerAdapter.ts": 175,
    "app/web/components/report/gene-viewer/useReportGeneViewer.ts": 275,
    "app/web/components/report/PopulationFrequencySection.tsx": 350,
    "app/web/components/report/PopulationAgeDistribution.tsx": 325,
    "app/web/components/report/population-frequency/PopulationFrequencyAncestry.tsx": 650,
    "app/web/components/report/population-frequency/PopulationFrequencyMap.tsx": 600,
    "app/web/components/report/population-frequency/PopulationUnavailablePanel.tsx": 50,
    "app/web/components/report/population-frequency/populationFrequencyModel.ts": 275,
    "app/web/components/report/ReportClient.tsx": 175,
    "app/web/components/report/report-client/ReportBody.tsx": 725,
    "app/web/components/report/report-client/ReportLoadStates.tsx": 375,
    "app/web/components/report/report-client/ReportSectionPrimitives.tsx": 325,
    "app/web/components/report/report-client/reportClientModel.ts": 225,
    "app/web/components/report/report-client/useReportClient.ts": 300,
    "app/web/components/compare/CompareClient.tsx": 1200,
    "app/web/components/compare/batchRunModel.ts": 250,
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


def test_legacy_vite_frontend_stays_retired() -> None:
    assert not (ROOT / "app" / "frontend").exists(), (
        "app/frontend was retired after its useful pure tests moved to app/web. "
        "Do not restore a second hand-maintained frontend or contract mirror."
    )


def test_root_package_exposes_one_repo_gate_without_vite_dependencies() -> None:
    package = json.loads(_read(ROOT / "package.json"))
    scripts = package.get("scripts", {})
    assert {"audit", "build", "guard", "lint", "test", "typecheck", "verify"}.issubset(scripts)
    assert all("eamos-repo-gate.mjs" in scripts[name] for name in scripts if name != "prepare")
    assert "vite" not in package.get("dependencies", {})
    assert "vite" not in package.get("devDependencies", {})


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


def test_lookup_service_facade_preserves_package_fold_import_surface() -> None:
    from app.services.lookup_service import (
        CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX,
        FUNCTIONAL_EVIDENCE_CACHE_VERSION,
        GENE_CONTEXT_SNAPSHOT_CACHE_VERSION,
        LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING,
        LEGACY_REPORT_SHELL_CACHE_READ_WARNING,
        PUBLICATION_DATA_CACHE_VERSION,
        REPORT_SECTION_CACHE_VERSION,
        REPORT_SHELL_CACHE_VERSION,
        SOURCE_RESULT_CACHE_VERSION,
        STRICT_GENOMIC_CACHE_VERSION,
        GENE_THERAPY_MAP,
        LookupService,
        _clinvar_distribution_runtime_path,
        _clinvar_gene_distribution_exclusion_warning,
    )

    assert LookupService.__name__ == "LookupService"
    assert GENE_THERAPY_MAP["RPE65"]
    assert CLINVAR_GENE_DISTRIBUTION_EXCLUDED_PENDING_INDEX
    assert PUBLICATION_DATA_CACHE_VERSION >= 1
    assert STRICT_GENOMIC_CACHE_VERSION >= 1
    assert FUNCTIONAL_EVIDENCE_CACHE_VERSION >= 1
    assert GENE_CONTEXT_SNAPSHOT_CACHE_VERSION >= 1
    assert REPORT_SHELL_CACHE_VERSION >= 1
    assert REPORT_SECTION_CACHE_VERSION >= 1
    assert SOURCE_RESULT_CACHE_VERSION >= 1
    assert LEGACY_REPORT_SHELL_CACHE_READ_WARNING
    assert LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING
    assert callable(_clinvar_distribution_runtime_path)
    assert callable(_clinvar_gene_distribution_exclusion_warning)
