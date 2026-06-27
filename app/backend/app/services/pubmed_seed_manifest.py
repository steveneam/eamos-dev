from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
import json
from pathlib import Path
import re
from typing import Any

from app.services.pubmed_local import PubMedSeedQuery

ALLOWED_CORPUS_LABELS = frozenset({"proof", "targeted_seed", "filtered_pubmed", "raw_mirror"})
ALLOWED_SCOPES = frozenset({"gene", "variant"})
ALLOWED_LITERATURE_LANES = frozenset({"pubmed", "litvar2", "pubtator", "pmc_license"})
PUBMED_TSV_FIELDS = (
    "gene",
    "cdna",
    "transcript",
    "protein_change",
    "rsid",
    "genomic_hg38",
    "scope",
)
PUBMED_ALIAS_FIELDS = frozenset(PUBMED_TSV_FIELDS) - {"gene", "scope"}
DISALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "bearer_token",
        "clinical_note",
        "cookie",
        "patient_id",
        "patient_note",
        "patient_text",
        "prompt",
        "raw_text",
        "request_body",
        "request_headers",
        "signed_url",
        "user_id",
    }
)
DISALLOWED_VALUE_FRAGMENTS = (
    "authorization:",
    "bearer ",
    "service_role",
    "supabase_storage_s3",
    "patient note",
    "request header",
    "request body",
    "signed url",
    "signed_url",
    "c:\\",
    "d:\\",
    "/var/data/",
)


class PubMedSeedManifestError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class LiteratureSeed:
    seed_id: str
    gene: str
    scope: str
    corpus_label: str
    source_rationale: str
    variant_aliases: dict[str, str]
    literature_lanes: tuple[str, ...]
    disease_terms: tuple[str, ...] = ()
    intervention_terms: tuple[str, ...] = ()

    def to_pubmed_seed_query(self) -> PubMedSeedQuery:
        return PubMedSeedQuery(
            gene=self.gene,
            cdna=self.variant_aliases.get("cdna"),
            transcript=self.variant_aliases.get("transcript"),
            protein_change=self.variant_aliases.get("protein_change"),
            rsid=self.variant_aliases.get("rsid"),
            genomic_hg38=self.variant_aliases.get("genomic_hg38"),
            scope=self.scope,
        )

    def to_pubmed_tsv_row(self) -> dict[str, str]:
        query = self.to_pubmed_seed_query()
        return {
            "gene": query.gene,
            "cdna": query.cdna or "",
            "transcript": query.transcript or "",
            "protein_change": query.protein_change or "",
            "rsid": query.rsid or "",
            "genomic_hg38": query.genomic_hg38 or "",
            "scope": query.scope,
        }


@dataclass(frozen=True)
class LiteratureSeedManifest:
    version: str
    defined_at: str
    purpose: str
    corpus_label: str
    source_scope: str
    seeds: tuple[LiteratureSeed, ...]

    @property
    def seed_count(self) -> int:
        return len(self.seeds)

    @property
    def corpus_labels(self) -> tuple[str, ...]:
        return tuple(sorted({seed.corpus_label for seed in self.seeds}))

    @property
    def genes(self) -> tuple[str, ...]:
        return tuple(sorted({seed.gene for seed in self.seeds}))

    def to_pubmed_seed_queries(self) -> list[PubMedSeedQuery]:
        return [seed.to_pubmed_seed_query() for seed in self.seeds]

    def to_pubmed_query_tsv(self) -> str:
        handle = StringIO()
        writer = csv.DictWriter(
            handle,
            fieldnames=PUBMED_TSV_FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for seed in self.seeds:
            writer.writerow(seed.to_pubmed_tsv_row())
        return handle.getvalue()

    def write_pubmed_query_tsv(self, path: Path, *, force: bool = False) -> None:
        if path.exists() and not force:
            raise PubMedSeedManifestError([f"output exists: {path.name}"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_pubmed_query_tsv(), encoding="utf-8", newline="\n")

    def to_sanitized_dict(self) -> dict[str, Any]:
        scope_counts: dict[str, int] = {}
        lane_counts: dict[str, int] = {}
        for seed in self.seeds:
            scope_counts[seed.scope] = scope_counts.get(seed.scope, 0) + 1
            for lane in seed.literature_lanes:
                lane_counts[lane] = lane_counts.get(lane, 0) + 1
        return {
            "version": self.version,
            "defined_at": self.defined_at,
            "corpus_label": self.corpus_label,
            "source_scope": self.source_scope,
            "ready": True,
            "seed_count": self.seed_count,
            "genes": self.genes,
            "corpus_labels": self.corpus_labels,
            "scope_counts": dict(sorted(scope_counts.items())),
            "literature_lane_counts": dict(sorted(lane_counts.items())),
            "guardrails": {
                "network": {"used": False, "provider": None},
                "source_download": "not_used",
                "materialization": "not_used",
                "storage_upload": "not_used",
                "runtime_flag_change": "not_used",
                "user_data": "not_allowed",
                "patient_data": "not_allowed",
                "request_payloads": "not_allowed",
            },
        }


def load_seed_manifest(path: Path) -> LiteratureSeedManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PubMedSeedManifestError(["seed manifest could not be read"]) from exc
    return parse_seed_manifest(payload)


def parse_seed_manifest(payload: Any) -> LiteratureSeedManifest:
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise PubMedSeedManifestError(["manifest root must be an object"])

    _scan_disallowed_payload(payload, errors)
    version = _required_text(payload, "version", errors)
    defined_at = _required_text(payload, "defined_at", errors)
    purpose = _required_text(payload, "purpose", errors)
    corpus_label = _required_text(payload, "corpus_label", errors)
    source_scope = _required_text(payload, "source_scope", errors)
    if corpus_label and corpus_label not in ALLOWED_CORPUS_LABELS:
        errors.append(f"unsupported corpus_label: {corpus_label}")

    seed_payloads = payload.get("seeds")
    if not isinstance(seed_payloads, list) or not seed_payloads:
        errors.append("seeds must be a non-empty list")
        seed_payloads = []

    seeds: list[LiteratureSeed] = []
    seen_seed_ids: set[str] = set()
    for index, item in enumerate(seed_payloads, start=1):
        if not isinstance(item, dict):
            errors.append(f"seed {index} must be an object")
            continue
        seed = _parse_seed(
            item,
            index=index,
            manifest_corpus_label=corpus_label,
            errors=errors,
        )
        if seed is None:
            continue
        if seed.seed_id in seen_seed_ids:
            errors.append(f"seed {index} duplicates seed_id {seed.seed_id}")
        seen_seed_ids.add(seed.seed_id)
        seeds.append(seed)

    if errors:
        raise PubMedSeedManifestError(errors)
    return LiteratureSeedManifest(
        version=version,
        defined_at=defined_at,
        purpose=purpose,
        corpus_label=corpus_label,
        source_scope=source_scope,
        seeds=tuple(seeds),
    )


def _parse_seed(
    item: dict[str, Any],
    *,
    index: int,
    manifest_corpus_label: str,
    errors: list[str],
) -> LiteratureSeed | None:
    seed_id = _required_text(item, "seed_id", errors, prefix=f"seed {index}")
    gene = _required_text(item, "gene", errors, prefix=f"seed {index}").upper()
    scope = _required_text(item, "scope", errors, prefix=f"seed {index}").lower()
    corpus_label = (
        _required_text(item, "corpus_label", errors, prefix=f"seed {index}")
        or manifest_corpus_label
    )
    source_rationale = _required_text(item, "source_rationale", errors, prefix=f"seed {index}")
    if seed_id and not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,63}", seed_id):
        errors.append(f"seed {index} has invalid seed_id")
    if gene and not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{1,24}", gene):
        errors.append(f"seed {index} has invalid gene")
    if scope and scope not in ALLOWED_SCOPES:
        errors.append(f"seed {index} has unsupported scope {scope}")
    if corpus_label and corpus_label not in ALLOWED_CORPUS_LABELS:
        errors.append(f"seed {index} has unsupported corpus_label {corpus_label}")
    if corpus_label and manifest_corpus_label and corpus_label != manifest_corpus_label:
        errors.append(f"seed {index} corpus_label must match manifest corpus_label")
    if source_rationale and len(source_rationale) > 280:
        errors.append(f"seed {index} source_rationale is too long")

    aliases = _variant_aliases(item.get("variant_aliases"), index=index, errors=errors)
    pubmed_alias_count = sum(1 for field in PUBMED_ALIAS_FIELDS if aliases.get(field))
    if scope == "variant" and pubmed_alias_count == 0:
        errors.append(f"seed {index} variant scope needs a PubMed-compatible variant alias")

    lanes = _text_list(
        item.get("literature_lanes"), index=index, field="literature_lanes", errors=errors
    )
    for lane in lanes:
        if lane not in ALLOWED_LITERATURE_LANES:
            errors.append(f"seed {index} has unsupported literature lane {lane}")

    trials = item.get("clinical_trials") or {}
    if not isinstance(trials, dict):
        errors.append(f"seed {index} clinical_trials must be an object when present")
        trials = {}
    disease_terms = _text_list(
        trials.get("disease_terms"),
        index=index,
        field="clinical_trials.disease_terms",
        errors=errors,
        required=False,
    )
    intervention_terms = _text_list(
        trials.get("intervention_terms"),
        index=index,
        field="clinical_trials.intervention_terms",
        errors=errors,
        required=False,
    )

    if not seed_id or not gene or not scope or not corpus_label or not source_rationale:
        return None
    return LiteratureSeed(
        seed_id=seed_id,
        gene=gene,
        scope=scope,
        corpus_label=corpus_label,
        source_rationale=source_rationale,
        variant_aliases=aliases,
        literature_lanes=tuple(lanes),
        disease_terms=tuple(disease_terms),
        intervention_terms=tuple(intervention_terms),
    )


def _variant_aliases(value: Any, *, index: int, errors: list[str]) -> dict[str, str]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        errors.append(f"seed {index} variant_aliases must be an object")
        return {}
    aliases: dict[str, str] = {}
    for field in PUBMED_ALIAS_FIELDS:
        cleaned = _clean_text(value.get(field))
        if cleaned:
            aliases[field] = cleaned
    return aliases


def _required_text(
    payload: dict[str, Any],
    field: str,
    errors: list[str],
    *,
    prefix: str = "manifest",
) -> str:
    value = _clean_text(payload.get(field))
    if not value:
        errors.append(f"{prefix} missing {field}")
        return ""
    return value


def _text_list(
    value: Any,
    *,
    index: int,
    field: str,
    errors: list[str],
    required: bool = True,
) -> list[str]:
    if value is None:
        if required:
            errors.append(f"seed {index} missing {field}")
        return []
    if not isinstance(value, list):
        errors.append(f"seed {index} {field} must be a list")
        return []
    result = [_clean_text(item) for item in value]
    result = [item for item in result if item]
    if required and not result:
        errors.append(f"seed {index} {field} must not be empty")
    return result


def _scan_disallowed_payload(value: Any, errors: list[str], *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")
            if normalized_key in DISALLOWED_PAYLOAD_KEYS:
                errors.append(f"{path}.{key} is not allowed in a seed manifest")
            _scan_disallowed_payload(item, errors, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _scan_disallowed_payload(item, errors, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        lower = value.lower()
        for fragment in DISALLOWED_VALUE_FRAGMENTS:
            if fragment in lower:
                errors.append(f"{path} contains disallowed sensitive text")
                break


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()
