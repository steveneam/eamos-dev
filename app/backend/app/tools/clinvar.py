from __future__ import annotations

from pathlib import Path

import httpx

from app.services.clinvar_local import ClinVarIndexedLocalAdapter, ClinVarLocalLookup
from app.services.local_evidence_orchestrator import LocalEvidenceRuntimeGate
from app.services.sequence_context import genomic_variant_id_to_refseq_hgvs
from app.tools.base import FixtureBackedTool, ToolResult

SUBMITTER_COUNT_LABELS = (
    "Pathogenic",
    "Likely pathogenic",
    "VUS",
    "Likely benign",
    "Benign",
)

_CLASSIFICATION_ALIASES = {
    "pathogenic": "Pathogenic",
    "likely pathogenic": "Likely pathogenic",
    "likely_pathogenic": "Likely pathogenic",
    "uncertain significance": "VUS",
    "uncertain_significance": "VUS",
    "vus": "VUS",
    "likely benign": "Likely benign",
    "likely_benign": "Likely benign",
    "benign": "Benign",
}


def _extract_cdna(transcript_hgvs: str | None) -> str | None:
    if not transcript_hgvs:
        return None
    parts = transcript_hgvs.split(":")
    return parts[-1] if len(parts) > 1 else transcript_hgvs


def _clinvar_search_url(term: str | None) -> str | None:
    if not term:
        return None
    return f"https://www.ncbi.nlm.nih.gov/clinvar/?term={term}"


def _clinvar_file_date_iso(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    return text or None


def _unavailable_summary(gene: str | None) -> dict:
    return {
        "gene": gene or "",
        "protein_change": None,
        "classification": "Unavailable",
        "review_status": "not found",
        "conditions": [],
        "consequence": "",
        "accession": None,
        "submitter_counts": {},
    }


def _normalized_classification(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    key = " ".join(value.replace("_", " ").strip().lower().split())
    if key in {
        "conflicting classifications of pathogenicity",
        "conflicting interpretations of pathogenicity",
    }:
        return None
    return _CLASSIFICATION_ALIASES.get(key)


def _supporting_submission_count(payload: dict) -> int:
    supporting = payload.get("supporting_submissions")
    if not isinstance(supporting, dict):
        return 0
    scv = supporting.get("scv")
    if not isinstance(scv, list):
        return 0
    return len([item for item in scv if item])


def _iter_classification_values(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {
                "classification",
                "classification_description",
                "classificationDescription",
                "clinical_significance",
                "clinicalSignificance",
                "description",
                "germlineClassificationDescription",
            }:
                yield child
            yield from _iter_classification_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_classification_values(child)


def _submitter_counts_from_payload(payload: dict) -> dict[str, int]:
    counts = {label: 0 for label in SUBMITTER_COUNT_LABELS}
    for value in _iter_classification_values(payload.get("submitter_classifications")):
        label = _normalized_classification(value)
        if label:
            counts[label] += 1
    for value in _iter_classification_values(payload.get("submissions")):
        label = _normalized_classification(value)
        if label:
            counts[label] += 1

    non_zero = {label: count for label, count in counts.items() if count > 0}
    if non_zero:
        return non_zero

    classification = _normalized_classification(
        (payload.get("germline_classification") or {}).get("description")
        if isinstance(payload.get("germline_classification"), dict)
        else None
    )
    if classification is None:
        return {}
    supporting_count = _supporting_submission_count(payload)
    return {classification: max(1, supporting_count)}


def _fixture_matches_variant(variant, fixture: dict) -> bool:
    if variant is None:
        return True
    summary = fixture.get("summary", {}) if isinstance(fixture, dict) else {}
    fixture_gene = str(summary.get("gene") or "").upper()
    request_gene = str(getattr(variant, "gene", "") or "").upper()
    if fixture_gene and request_gene and fixture_gene != request_gene:
        return False
    search_text = _source_search_text(variant).lower()
    request_variant_id = str(getattr(variant, "genomic_hg38", "") or "").lower()
    request_genomic_hgvs = str(getattr(variant, "genomic_hgvs", "") or "").lower()
    return any(
        token in search_text or token in request_variant_id or token in request_genomic_hgvs
        for token in ("c.260a>g", "1-68444869-t-c", "68444869t>c")
    )


def _source_search_text(variant) -> str:
    gene = getattr(variant, "gene", "") or ""
    genomic_hgvs = getattr(variant, "genomic_hgvs", "") or ""
    if genomic_hgvs:
        return genomic_hgvs

    genomic_hg38 = getattr(variant, "genomic_hg38", "") or ""
    inferred_genomic_hgvs = (
        genomic_variant_id_to_refseq_hgvs(genomic_hg38) if genomic_hg38 else None
    )
    if inferred_genomic_hgvs:
        return inferred_genomic_hgvs

    source_inputs = getattr(
        getattr(variant, "search_input_resolution", None), "source_inputs", None
    )
    search_text = getattr(source_inputs, "clinvar", None) if source_inputs is not None else None
    if search_text:
        return search_text

    transcript_hgvs = getattr(variant, "transcript_hgvs", None)
    cdna = _extract_cdna(transcript_hgvs)
    return f"{gene}:{cdna}" if cdna else gene


def _local_lookup_to_tool_result(
    lookup: ClinVarLocalLookup,
    *,
    variant,
    variant_id: str,
) -> ToolResult:
    record = lookup.record
    if record is None:
        raise ValueError("local ClinVar lookup result must include a record")
    summary = {
        "gene": (record.gene_symbols[0] if record.gene_symbols else getattr(variant, "gene", "")),
        "protein_change": _protein_change_from_record(record.hgvs_aliases, variant),
        "classification": record.classification,
        "review_status": record.review_status,
        "conditions": list(record.conditions),
        "consequence": "",
        "accession": record.accession,
        "submitter_counts": {},
        "dbsnp_rsid": getattr(variant, "dbsnp_rsid", None),
        "source_version": record.provenance.source_version,
        "upstream_released_at": _clinvar_file_date_iso(record.provenance.file_date),
    }
    return ToolResult(
        source="clinvar",
        status="local",
        request_identity={"variant_id": variant_id, "clinvar_id": record.variation_id},
        summary=summary,
        warnings=list(lookup.warnings),
        raw={
            "variant_id": record.gnomad_variant_id,
            "accession": record.accession,
            "variation_id": record.variation_id,
            "classification": record.classification,
            "review_status": record.review_status,
            "conditions": list(record.conditions),
            "hgvs_aliases": list(record.hgvs_aliases),
            "gene_symbols": list(record.gene_symbols),
            "source_id": record.provenance.source_id,
            "source_status": "local",
        },
        source_url=f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{record.variation_id}/",
        source_version=record.provenance.source_version,
    )


def _protein_change_from_record(hgvs_aliases: tuple[str, ...], variant) -> str | None:
    explicit = getattr(variant, "protein_change", None)
    if explicit:
        return explicit
    for alias in hgvs_aliases:
        marker = ":p."
        if marker in alias:
            return alias.split(marker, 1)[1]
    return None


class ClinvarTool(FixtureBackedTool):
    source = "clinvar"
    fixture_name = "clinvar_fixtures.json"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self._local_adapter: ClinVarIndexedLocalAdapter | None = None
        self._local_adapter_key: tuple[Path, Path] | None = None

    def get_evidence(self, variant=None) -> ToolResult:
        if not self.settings.use_real_apis or variant is None:
            fixture = self.load_fixture()
            gene = (variant.gene if variant is not None else None) or ""
            fallback_url = (
                f"https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]" if gene else None
            )
            if variant is not None and not _fixture_matches_variant(variant, fixture):
                return ToolResult(
                    source=self.source,
                    status="missing",
                    request_identity={"search_text": _source_search_text(variant)},
                    summary=_unavailable_summary(gene),
                    warnings=["clinvar_fixture_variant_mismatch"],
                    raw=None,
                    source_url=_clinvar_search_url(_source_search_text(variant) or gene),
                )
            return ToolResult(
                source=self.source, status="fixture", source_url=fallback_url, **fixture
            )
        local_result = self._get_local_evidence(variant)
        if local_result is not None and local_result.status == "local":
            return local_result
        try:
            live_result = self._fetch_live(variant)
        except Exception as exc:
            gene = variant.gene or ""
            search_text = _source_search_text(variant)
            live_result = ToolResult(
                source=self.source,
                status="fallback",
                request_identity={"search_text": search_text or gene},
                summary=_unavailable_summary(gene),
                warnings=[f"live_fetch_failed:{type(exc).__name__}"],
                raw=None,
                source_url=_clinvar_search_url(search_text or gene),
            )
        if local_result is not None:
            live_result.warnings = [*local_result.warnings, *live_result.warnings]
        return live_result

    def _get_local_evidence(self, variant) -> ToolResult | None:
        if not LocalEvidenceRuntimeGate.from_settings(self.settings).allows("lookup"):
            return None
        variant_id = getattr(variant, "genomic_hg38", None)
        if not variant_id:
            return ToolResult(
                source=self.source,
                status="missing",
                request_identity={"search_text": _source_search_text(variant)},
                summary=_unavailable_summary(getattr(variant, "gene", None)),
                warnings=["clinvar_local_requires_resolved_variant_id"],
                raw=None,
                source_url=_clinvar_search_url(_source_search_text(variant)),
            )
        lookup = self._local_adapter_for_settings().lookup_variant_id(variant_id)
        if not lookup.available or lookup.record is None:
            return ToolResult(
                source=self.source,
                status="missing",
                request_identity={"variant_id": variant_id},
                summary=_unavailable_summary(getattr(variant, "gene", None)),
                warnings=list(lookup.warnings),
                raw={"local_unavailable_reason": lookup.unavailable_reason},
                source_url=_clinvar_search_url(_source_search_text(variant)),
            )
        return _local_lookup_to_tool_result(lookup, variant=variant, variant_id=variant_id)

    def _local_adapter_for_settings(self) -> ClinVarIndexedLocalAdapter:
        vcf_path = Path(self.settings.clinvar_runtime_vcf_path)
        index_path = Path(self.settings.clinvar_runtime_index_path)
        key = (vcf_path, index_path)
        if self._local_adapter is None or self._local_adapter_key != key:
            if self._local_adapter is not None:
                self._local_adapter.close()
            self._local_adapter = ClinVarIndexedLocalAdapter.from_settings(self.settings)
            self._local_adapter_key = key
        return self._local_adapter

    def _fetch_live(self, variant) -> ToolResult:
        gene = variant.gene
        search_text = _source_search_text(variant)

        # Step 1: resolve search term to ClinVar variation ID
        search_response = httpx.get(
            f"{self.settings.clinvar_base_url}/esearch.fcgi",
            params={"db": "clinvar", "term": search_text, "retmode": "json"},
            timeout=10.0,
        )
        search_response.raise_for_status()
        id_list = search_response.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return ToolResult(
                source=self.source,
                status="live",
                request_identity={"search_text": search_text},
                summary=_unavailable_summary(gene),
                warnings=["clinvar_variant_not_found"],
                raw={},
                source_url=_clinvar_search_url(search_text),
            )
        clinvar_id = id_list[0]

        # Step 2: fetch summary for that ID
        summary_response = httpx.get(
            f"{self.settings.clinvar_base_url}/esummary.fcgi",
            params={"db": "clinvar", "id": clinvar_id, "retmode": "json"},
            timeout=10.0,
        )
        summary_response.raise_for_status()
        payload = summary_response.json()["result"][clinvar_id]
        summary = {
            "gene": payload["genes"][0]["symbol"] if payload.get("genes") else gene,
            "protein_change": payload.get("protein_change"),
            "classification": payload["germline_classification"]["description"],
            "review_status": payload["germline_classification"]["review_status"],
            "conditions": [
                item["trait_name"] for item in payload["germline_classification"]["trait_set"]
            ],
            "consequence": (payload.get("molecular_consequence_list") or [""])[0],
            "accession": payload.get("accession"),
            "submitter_counts": _submitter_counts_from_payload(payload),
        }
        return ToolResult(
            source=self.source,
            status="live",
            request_identity={"search_text": search_text, "clinvar_id": clinvar_id},
            summary=summary,
            raw=payload,
            source_url=f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{clinvar_id}/",
        )
