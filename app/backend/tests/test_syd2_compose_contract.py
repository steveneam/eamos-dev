from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = ROOT / "deploy" / "syd2" / "compose.yaml"
IMAGE = (
    "ghcr.io/steveneam/eamos-backend@sha256:"
    "910dc159b3b2de8fec8f389ec7c328a6046733403793ba5f98b6cf83155a3fe1"
)

EXPECTED_ENVIRONMENT = {
    "ADMIN_MATERIALIZATION_ENABLED",
    "AI_CHAT_DEV_DAILY_CAP",
    "AI_CHAT_DEV_DAILY_CAP_ENABLED",
    "AI_CHAT_USER_DAILY_CAP",
    "AI_CHAT_USER_DAILY_CAP_ENABLED",
    "AI_CHAT_USER_DAILY_CAP_WINDOW_SECONDS",
    "AI_GATEWAY_API_KEY",
    "ALLOWED_ORIGINS_RAW",
    "ALPHAMISSENSE_HG38_RUNTIME_ASSET_MODE",
    "ALPHAMISSENSE_HG38_RUNTIME_ASSET_PATH",
    "APP_NAME",
    "CLINGEN_LOCAL_ENABLED",
    "CLINGEN_LOCAL_MANIFEST_PATH",
    "CLINGEN_LOCAL_SQLITE_PATH",
    "CLINVAR_GENE_DISTRIBUTION_INDEX_PATH",
    "CLINVAR_GENE_DISTRIBUTION_MANIFEST_PATH",
    "CLINVAR_RUNTIME_INDEX_PATH",
    "CLINVAR_RUNTIME_VCF_PATH",
    "COORDINATE_RESOLVER_ASSET_MATERIALIZATION_ENABLED",
    "COORDINATE_RESOLVER_COMPACT_INDEX_MAX_TRANSCRIPTS",
    "COORDINATE_RESOLVER_COMPACT_INDEX_PATH",
    "COORDINATE_RESOLVER_MANE_GFF_PATH",
    "COORDINATE_RESOLVER_REFSEQ_GFF_PATH",
    "DATABASE_URL",
    "DBSNP_RUNTIME_INDEX_PATH",
    "DBSNP_RUNTIME_VCF_PATH",
    "DEBUG",
    "ENV",
    "FINAL_REPORT_DIR",
    "HG38_2BIT_RUNTIME_ASSET_PATH",
    "HOST",
    "JWT_SECRET",
    "LLM_PROVIDER",
    "LOCAL_EVIDENCE_ALLOWED_FLOWS_RAW",
    "LOCAL_EVIDENCE_ENABLED",
    "LOCAL_EVIDENCE_REQUIRE_REAL_APIS",
    "PHYLOP_RUNTIME_BIGWIG_PATH",
    "PORT",
    "PROTEIN_ANNOTATION_ENABLED",
    "PROTEIN_ANNOTATION_PFAM_HMM_GZ_PATH",
    "PROTEIN_ANNOTATION_PFAM_HMM_PATH",
    "PUBMED_LOCAL_STARTUP_MATERIALIZATION_ENABLED",
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_TRUST_PROXY_HEADERS",
    "REPEATMASKER_RUNTIME_INDEX_PATH",
    "SENTRY_DSN",
    "SENTRY_ENVIRONMENT",
    "SUPABASE_JWT_ALGORITHM",
    "SUPABASE_LOCAL_MODEL_CACHE_DATABASE_URL",
    "SUPABASE_LOCAL_MODEL_CACHE_ENABLED",
    "SUPABASE_LOCAL_MODEL_CACHE_SCHEMA",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_URL",
    "UPLOAD_DIR",
    "USE_REAL_APIS",
}


def _compose_text() -> str:
    return COMPOSE_PATH.read_text(encoding="utf-8")


def _environment_lines(text: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index("    environment:") + 1
    out: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith("      "):
            break
        if line.strip():
            out.append(line)
    return out


def test_syd2_compose_pins_identity_image_and_security_boundary() -> None:
    text = _compose_text()

    assert f"    image: {IMAGE}" in text
    assert '    user: "1000:1000"' in text
    assert "      - umask 077 && exec uvicorn" in text
    assert "    read_only: true" in text
    assert "    cap_drop:\n      - ALL" in text
    assert "      - no-new-privileges:true" in text
    assert "      - /tmp:size=536870912,mode=1777" in text
    assert "          pids: 256" in text
    assert "    privileged:" not in text
    assert "    ports:" not in text
    assert "/var/run/docker.sock" not in text


def test_syd2_compose_mounts_only_the_frozen_corpus_and_private_state() -> None:
    text = _compose_text()

    assert "      - /srv/project1/assets/runtime:/app/data/bio_assets:ro" in text
    assert "      - /srv/project1/assets/runtime:/var/data/eamos/bio_assets:ro" in text
    assert "      - /srv/project1/app-state:/app/state" in text
    assert "- /srv/project1/assets:/" not in text
    assert "          memory: 2G" in text
    assert "          memory: 512M" in text
    assert '          cpus: "2.0"' in text
    assert '          cpus: "0.25"' in text
    assert "    healthcheck:" in text
    assert "http://127.0.0.1:8000/healthz" in text
    assert "  dokploy-network:\n    external: true" in text


def test_syd2_compose_environment_is_an_exact_placeholder_only_allowlist() -> None:
    environment_lines = _environment_lines(_compose_text())
    parsed: dict[str, str] = {}
    for line in environment_lines:
        match = re.fullmatch(r" {6}([A-Z][A-Z0-9_]*): (.+)", line)
        assert match is not None, f"unexpected environment line: {line!r}"
        key, value = match.groups()
        assert key not in parsed
        parsed[key] = value

    assert set(parsed) == EXPECTED_ENVIRONMENT
    assert len(parsed) == 55
    for key, value in parsed.items():
        assert value == f"${{{key}:?required}}"

    assert not any(key.startswith("SUPABASE_STORAGE_S3_") for key in parsed)
    assert "ADMIN_MATERIALIZATION_TOKEN_SHA256" not in parsed
