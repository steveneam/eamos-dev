from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

FIXTURE_SCHEMA_VERSION = "mavedb.bulk.synthetic.v4"


def score_set(
    urn: str,
    rows: list[dict[str, str]],
    *,
    license_short_name: str | None = "CC0",
    license_version: str | None = "1.0",
    data_usage_policy: str | None = None,
    target_accession: str = "NM_000329.3",
    target_assembly: str | None = None,
    target_gene: str = "RPE65",
    target_id: int = 1,
    target_genes: list[dict[str, Any]] | None = None,
    superseded_by: str | None = None,
    private: bool = False,
    expected_variant_count: int | None = None,
) -> dict[str, Any]:
    experiment_urn = urn.rsplit("-", 1)[0]
    numeric_columns = _numeric_columns(rows)
    metadata = {
        column: {
            "description": "Primary assay score" if column == "score" else f"Source {column}",
            "details": "Assay-specific; no cross-assay direction is implied",
        }
        for column in numeric_columns
    }
    license_payload = (
        {
            "shortName": license_short_name,
            "version": license_version,
        }
        if license_short_name is not None
        else None
    )
    target_payload = target_genes or [
        {
            "id": target_id,
            "name": target_gene,
            "mappedHgncName": target_gene,
            "targetAccession": {
                "accession": target_accession,
                "assembly": target_assembly,
                "gene": target_gene,
            },
            "targetSequence": None,
        }
    ]
    return {
        "urn": urn,
        "recordType": "ScoreSet",
        "experimentUrn": experiment_urn,
        "title": f"Synthetic score set {urn}",
        "shortDescription": "Synthetic MAVE assay context",
        "methodText": "Scores were normalized within this synthetic assay only.",
        "license": license_payload,
        "dataUsagePolicy": data_usage_policy,
        "numVariants": len(rows) if expected_variant_count is None else expected_variant_count,
        "targetGenes": target_payload,
        "datasetColumns": {
            "scoreColumns": numeric_columns,
            "countColumns": None,
            "scoreColumnsMetadata": metadata,
        },
        "supersedingScoreSet": {"urn": superseded_by} if superseded_by else None,
        "private": private,
        "doiIdentifiers": [{"identifier": "10.1000/synthetic.mave", "url": "https://evil"}],
        "primaryPublicationIdentifiers": [
            {"identifier": "12345678", "dbName": "PubMed", "url": "https://evil"}
        ],
        "secondaryPublicationIdentifiers": [],
        "source_url": "https://attacker.invalid/not-authoritative",
        "_fixture_rows": rows,
    }


def variant_row(
    urn: str,
    hgvs_nt: str,
    score: str,
    *,
    hgvs_splice: str = "NA",
    hgvs_pro: str = "NA",
    **values: str,
) -> dict[str, str]:
    return {
        "urn": urn,
        "hgvs_nt": hgvs_nt,
        "hgvs_splice": hgvs_splice,
        "hgvs_pro": hgvs_pro,
        "score": score,
        **values,
    }


def write_mavedb_archive(
    path: Path,
    score_sets: list[dict[str, Any]],
    *,
    extra_members: list[tuple[str | ZipInfo, str | bytes]] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    experiments: dict[str, dict[str, Any]] = {}
    experiment_sets: dict[str, dict[str, Any]] = {}
    public_score_sets: list[dict[str, Any]] = []
    csv_payloads: list[tuple[str, str]] = []
    for raw_score_set in score_sets:
        record = dict(raw_score_set)
        rows = record.pop("_fixture_rows")
        urn = str(record["urn"])
        experiment_urn = str(record["experimentUrn"])
        experiment_set_urn = experiment_urn.rsplit("-", 1)[0]
        experiments.setdefault(
            experiment_urn,
            {
                "urn": experiment_urn,
                "recordType": "Experiment",
                "experimentSetUrn": experiment_set_urn,
                "shortDescription": "Synthetic experiment context",
                "methodText": "Synthetic experiment method context.",
                "doiIdentifiers": [],
                "primaryPublicationIdentifiers": [],
                "secondaryPublicationIdentifiers": [],
            },
        )
        experiment_sets.setdefault(
            experiment_set_urn,
            {
                "urn": experiment_set_urn,
                "recordType": "ExperimentSet",
            },
        )
        public_score_sets.append(record)
        csv_payloads.append((f"{urn}_scores.csv", _score_csv(rows)))

    main = {
        "schemaVersion": FIXTURE_SCHEMA_VERSION,
        "experimentSets": list(experiment_sets.values()),
        "experiments": list(experiments.values()),
        "scoreSets": public_score_sets,
    }
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("main.json", json.dumps(main, sort_keys=True, separators=(",", ":")))
        for name, payload in csv_payloads:
            archive.writestr(name, payload)
        for name, payload in extra_members or []:
            archive.writestr(name, payload)
    return path


def _numeric_columns(rows: list[dict[str, str]]) -> list[str]:
    fixed = {
        "urn",
        "variant_urn",
        "hgvs_nt",
        "hgvs_splice",
        "hgvs_pro",
        "guide_sequence",
        "vrs_id",
        "ga4gh_vrs_id",
        "mapped_vrs_id",
        "genomic_identity",
        "genomic_hgvs",
        "mapped_hgvs",
        "mapping_assembly",
        "assembly",
    }
    ordered = ["score"]
    for row in rows:
        for column in row:
            if column not in fixed and column not in ordered:
                ordered.append(column)
    return ordered


def _score_csv(rows: list[dict[str, str]]) -> str:
    required = ["urn", "hgvs_nt", "hgvs_splice", "hgvs_pro"]
    fieldnames = list(required)
    for row in rows:
        for column in row:
            if column not in fieldnames:
                fieldnames.append(column)
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
