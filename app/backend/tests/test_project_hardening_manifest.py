from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "app" / "fixtures"
MANIFEST_PATH = FIXTURE_ROOT / "hardening" / "project_100_sample_manifest.json"
STACK_PATH = FIXTURE_ROOT / "tools" / "clinvar_gene_agnostic_report_stack.json"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_project_hardening_manifest_declares_correct_100_sample_shape() -> None:
    manifest = _json(MANIFEST_PATH)

    assert manifest["selection_policy"]["gene_count"] == 10
    assert manifest["selection_policy"]["samples_per_gene"] == 10
    assert manifest["selection_policy"]["control_samples_per_gene"] == 1
    assert manifest["selection_policy"]["challenge_samples_per_gene"] == 9
    assert manifest["selection_policy"]["total_samples"] == 100
    assert manifest["coverage"] == {
        "genes": 10,
        "samples": 100,
        "control_samples": 10,
        "challenge_samples": 90,
    }
    assert set(manifest["surfaces"]) == {"landing", "variant_report", "workbench"}
    assert manifest["sources"] == {
        "challenge_stack": "app/backend/app/fixtures/tools/clinvar_gene_agnostic_report_stack.json",
        "control_queries": "project_100_sample_manifest.genes[*].control_sample",
        "coordinate_resolver": "app/backend/app/services/eamos_coordinate_resolver.py",
    }


def test_project_hardening_manifest_resolves_to_stack_plus_controls() -> None:
    manifest = _json(MANIFEST_PATH)
    stack = _json(STACK_PATH)

    stack_by_gene = {entry["gene"]: entry["variants"] for entry in stack["stack_genes"]}
    manifest_genes = manifest["genes"]
    manifest_gene_names = [entry["gene"] for entry in manifest_genes]

    assert set(manifest_gene_names) == set(stack_by_gene)
    assert "RPE65" not in manifest_gene_names

    sample_ids: set[str] = set()
    sample_kinds: Counter[str] = Counter()

    for gene_entry in manifest_genes:
        gene = gene_entry["gene"]
        control = gene_entry["control_sample"]

        assert control["sample_id"] == f"HC-{gene}-CTRL"
        assert control["sample_id"] not in sample_ids
        sample_ids.add(control["sample_id"])
        sample_kinds[control["sample_kind"]] += 1

        assert control["sample_kind"] == "reference_control"
        assert control["source_fixture"] == "control_queries"
        assert control["workbench_viewer_mode"] == "reference"
        assert control["transcript"].startswith("NM_")
        assert control["cdna"].startswith("c.")
        assert control["accession"].startswith("VCV")
        assert control["clinvar_variation_id"].isdigit()
        assert control["clinical_significance"]
        assert control["query"] == {
            "gene": gene,
            "cdna": control["cdna"],
            "transcript_hgvs": f"{control['transcript']}:{control['cdna']}",
            "raw_text": f"{gene} {control['transcript']}:{control['cdna']}",
        }

        challenge = gene_entry["challenge_samples"]
        challenge_variants = stack_by_gene[gene]

        assert challenge == {
            "sample_id_prefix": f"HC-{gene}-CH",
            "sample_kind": "clinvar_challenge",
            "source_fixture": "challenge_stack",
            "source_gene": gene,
            "include_all_gene_variants": True,
            "expected_count": 9,
        }
        assert len(challenge_variants) == challenge["expected_count"]

        for index, variant in enumerate(challenge_variants, start=1):
            sample_id = f"{challenge['sample_id_prefix']}-{index:02d}"
            assert sample_id not in sample_ids
            sample_ids.add(sample_id)
            sample_kinds[challenge["sample_kind"]] += 1
            assert variant["gene"] == gene
            assert variant["report_query"]["gene"] == gene

    assert sample_kinds == {"reference_control": 10, "clinvar_challenge": 90}
    assert len(sample_ids) == 100


def test_project_hardening_manifest_does_not_redefine_old_stack_shape() -> None:
    manifest = _json(MANIFEST_PATH)
    stack = _json(STACK_PATH)

    assert manifest["selection_policy"]["do_not_mutate"] == [
        "app/backend/app/fixtures/tools/clinvar_gene_agnostic_report_stack.json"
    ]
    assert len(stack["stack_genes"]) == 10
    assert sum(len(entry["variants"]) for entry in stack["stack_genes"]) == 90
    assert stack["reference_control_gene"]["control_variant"]["gene"] == "RPE65"
