from __future__ import annotations

import json

from app.cli.eamos_workbench_render_approval_bundle import (
    build_render_approval_bundle,
    main,
)


def test_render_approval_bundle_records_guardrails_and_env_gates() -> None:
    bundle = build_render_approval_bundle(generated_at="2026-06-13T00:00:00+00:00")

    assert bundle["mode"] == "workbench_render_approval_bundle"
    assert bundle["generated_at"] == "2026-06-13T00:00:00+00:00"
    assert bundle["guardrails"] == {
        "generated_assets_committed": False,
        "local_path_values_emitted": False,
        "mutations_performed": False,
        "network_used": False,
        "provider_flip_performed": False,
        "render_env_changed": False,
        "request_time_source_search_allowed": False,
        "secret_values_emitted": False,
        "startup_downloads_allowed": False,
    }

    env = bundle["env_changes"]
    assert env["do_not_change_before_approval"] == {
        "CRISPR_OFFTARGET_PROVIDER": "auto",
        "LLM_PROVIDER": "mock",
        "PRIMER_SPECIFICITY_PROVIDER": "template",
    }
    assert env["crispr_offtarget_flip_after_ready"] == {
        "CRISPR_OFFTARGET_INDEX_PATH": (
            "/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite"
        ),
        "CRISPR_OFFTARGET_PROVIDER": "indexed_sqlite",
    }
    assert (
        "dbSNP runtime VCF/TBI env names for primer SNP masking" in env["not_finalized_in_code_yet"]
    )

    paths = bundle["render_disk_layout"]
    assert paths["required_for_crispr_offtarget_flip"]["spcas9_sqlite"] == (
        "/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite"
    )
    assert paths["optional_for_primer_specificity"]["ucsc_ispcr_binary"] == (
        "/var/data/eamos/bio_assets/bin/isPcr"
    )
    assert paths["planned_for_gene_viewer_tracks"]["pfam_hmmpress_indexes"].endswith(
        "Pfam-A.hmm.h3*"
    )


def test_render_approval_bundle_preflight_and_smoke_are_specific() -> None:
    bundle = build_render_approval_bundle(generated_at="2026-06-13T00:00:00+00:00")

    preflight = {item["name"]: item for item in bundle["operator_preflight"]}
    assert "offtarget_index_verify" in preflight
    assert "eamos_crispr_offtarget_index verify" in preflight["offtarget_index_verify"]["command"]
    assert preflight["offtarget_index_verify"]["expects"] == {
        "genome_build_matches": True,
        "local_path_values_emitted": False,
        "target_count_meets_min": True,
        "verification_ready": True,
    }
    assert preflight["offtarget_index_manifest"]["expects"]["actual_sha256"] == "recorded"
    assert preflight["source_asset_preflight"]["expects"]["uploads_or_imports"] == "not_used"

    smoke = {item["name"]: item for item in bundle["post_flip_smoke"]}
    assert smoke["sg_healthz"]["expects"]["llm_provider"] == "mock"
    assert (
        smoke["sg_provider_cache"]["expects"][
            "providers.crispr.off_target_screening.indexed_sqlite.ready"
        ]
        is True
    )
    assert "POST /api/v1/crispr/offtargets" in smoke["workbench_api_probes"]["commands"]
    assert "POST /api/v1/crispr/tide" in smoke["workbench_api_probes"]["commands"]


def test_render_approval_bundle_includes_crispr_full_index_runbook() -> None:
    bundle = build_render_approval_bundle(generated_at="2026-06-13T00:00:00+00:00")

    runbook = bundle["crispr_offtarget_full_index_runbook"]
    source = runbook["input_source"]
    assert source == {
        "expected_md5": "dcc3ea27079aa6dc3f9deccd7275e0f8",
        "expected_path_on_build_host": "/var/data/eamos/bio_assets/genomes/hg38.2bit",
        "expected_size_bytes": 835_393_456,
        "genome_build": "GRCh38",
        "kind": "twobit",
        "source_name": "UCSC hg38.2bit",
        "source_version": "ucsc-hg38-md5-dcc3ea27079aa6dc3f9deccd7275e0f8",
        "verify_before_build": (
            "Get-FileHash -Algorithm MD5 /var/data/eamos/bio_assets/genomes/hg38.2bit"
        ),
    }

    full_build = runbook["full_build"]
    assert "--twobit /var/data/eamos/bio_assets/genomes/hg38.2bit" in full_build["command"]
    assert full_build["expected_output_path"] == (
        "/var/data/eamos/bio_assets/crispr/spcas9_offtargets.sqlite"
    )
    assert "do not commit generated SQLite" in full_build["artifact_policy"]

    flow = {item["step"]: item for item in runbook["checksum_manifest_flow"]}
    assert "eamos_crispr_offtarget_index estimate" in flow["estimate"]["command"]
    assert "eamos_crispr_offtarget_index verify" in flow["verify"]["command"]
    assert flow["verify"]["expects"]["verification_ready"] is True
    assert flow["manifest"]["records"] == ["actual_sha256", "target_count", "source_version"]

    pilot = runbook["pilot_tiny_proof"]
    assert pilot["expects"]["estimate_target_count_at_least"] == 1
    assert pilot["expects"]["manifest_actual_sha256_length"] == 64
    assert any("build --fasta <tiny.fa>" in command for command in pilot["commands"])

    readiness = runbook["provider_cache_readiness"]
    assert readiness["pre_flip_expected"] == {
        "configured_provider": "auto",
        "indexed_sqlite.ready": False,
        "request_time_supabase_search": False,
        "status": "mock_fallback",
    }
    assert readiness["post_flip_required"]["configured_provider"] == "indexed_sqlite"
    assert readiness["post_flip_required"]["indexed_sqlite.ready"] is True
    assert runbook["rollback_values"]["CRISPR_OFFTARGET_PROVIDER"] == "auto"


def test_render_approval_bundle_cli_is_sanitized(capsys) -> None:
    exit_code = main(["--compact"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload).lower()
    assert payload["mode"] == "workbench_render_approval_bundle"
    assert payload["guardrails"]["mutations_performed"] is False
    assert payload["guardrails"]["network_used"] is False
    assert "c:\\" not in encoded
    assert "d:\\" not in encoded
    assert "service_role" not in encoded
    assert "api_key" not in encoded
    assert "supabase://" not in encoded
