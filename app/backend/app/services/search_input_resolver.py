from __future__ import annotations

import re
import json
import time
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from app.services.compact_coordinate_index import DEFAULT_COMPACT_COORDINATE_INDEX_PATH
from app.services.eamos_coordinate_resolver import (
    EamosCoordinateResolution,
    EamosLocalCoordinateResolver,
)
from app.services.reference_genome import TwoBitReferenceGenomeStore
from app.services.sequence_context import (
    CANONICAL_TRANSCRIPTS,
    QueryKind,
    genomic_variant_id_to_refseq_hgvs,
    normalize_variant_query,
    parse_genomic_variant_id,
)


@dataclass(frozen=True)
class SourceSpecificInputs:
    variant_validator: str | None = None
    ensembl_vep: str | None = None
    gnomad: str | None = None
    spliceai: str | None = None
    clinvar: str | None = None
    literature_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoordinateResolutionAudit:
    resolver_path: str
    coordinate_resolution_requested: bool
    used_eamos_local: bool
    used_variant_validator: bool
    used_clinvar_for_coordinates: bool
    used_submitted_genomic: bool
    used_rsid_candidates: bool
    canonical_variant_id: str | None = None
    genomic_hgvs: str | None = None
    local_source: str | None = None
    variant_validator_url: str | None = None
    clinvar_role: str | None = None
    provenance: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RsidResolutionCandidate:
    candidate_id: str
    display_label: str
    rsid: str
    gene: str
    cdna: str
    transcript: str | None = None
    protein_change: str | None = None
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    variant_allele: str | None = None
    source_support: tuple[str, ...] = ()
    is_preferred: bool = False


@dataclass(frozen=True)
class ParsedSearchInput:
    submitted_text: str
    gene: str
    cdna: str
    transcript: str | None = None
    protein_change: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchInputResolution:
    gene: str
    hgvs: str
    transcript: str | None
    protein_change: str | None
    kind: QueryKind
    transcript_hgvs: str
    resolver_transcript: str | None
    resolver_transcript_hgvs: str
    genomic_hg38: str | None = None
    genomic_hgvs: str | None = None
    source_inputs: SourceSpecificInputs = field(default_factory=SourceSpecificInputs)
    warnings: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    variant_validator_summary: dict[str, Any] | None = None
    variant_validator_raw: dict[str, Any] | None = None
    variant_validator_url: str | None = None
    local_coordinate_summary: dict[str, Any] | None = None
    coordinate_resolution_audit: CoordinateResolutionAudit = field(
        default_factory=lambda: CoordinateResolutionAudit(
            resolver_path="unknown",
            coordinate_resolution_requested=False,
            used_eamos_local=False,
            used_variant_validator=False,
            used_clinvar_for_coordinates=False,
            used_submitted_genomic=False,
            used_rsid_candidates=False,
        )
    )
    rsid_candidates: tuple[RsidResolutionCandidate, ...] = ()


class EamosSearchInputResolver:
    """Resolve user variant input into source-specific identifiers."""

    def __init__(
        self,
        settings=None,
        *,
        timeout_seconds: float | None = None,
        resolve_coordinates: bool = False,
        local_coordinate_resolver: EamosLocalCoordinateResolver | None = None,
    ) -> None:
        self.settings = settings
        default_timeout = getattr(settings, "search_input_resolver_timeout_seconds", 5.0)
        self.timeout_seconds = _positive_float(
            default_timeout if timeout_seconds is None else timeout_seconds,
            default=5.0,
        )
        self.deadline_seconds = max(
            self.timeout_seconds,
            _positive_float(
                getattr(settings, "search_input_resolver_deadline_seconds", self.timeout_seconds),
                default=self.timeout_seconds,
            ),
        )
        self.resolve_coordinates = resolve_coordinates
        self._local_coordinate_resolver = local_coordinate_resolver

    def resolve_text(
        self,
        text: str,
        *,
        gene: str | None = None,
        transcript: str | None = None,
        protein_change: str | None = None,
    ) -> SearchInputResolution:
        parsed = parse_search_text(
            text,
            gene=gene,
            transcript=transcript,
            protein_change=protein_change,
        )
        resolution = self.resolve(
            gene=parsed.gene,
            cdna=parsed.cdna,
            transcript=parsed.transcript,
            protein_change=parsed.protein_change,
        )
        if not parsed.warnings:
            return resolution
        return replace(resolution, warnings=(*parsed.warnings, *resolution.warnings))

    def resolve(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        protein_change: str | None = None,
    ) -> SearchInputResolution:
        normalized_gene, hgvs, normalized_transcript, kind = normalize_variant_query(
            gene,
            cdna,
            transcript,
        )
        warnings: list[str] = []
        provenance: list[str] = []
        deadline = time.monotonic() + self.deadline_seconds

        transcript_hgvs = f"{normalized_transcript}:{hgvs}" if normalized_transcript else hgvs
        resolver_transcript = normalized_transcript
        if resolver_transcript is None and kind == "cdna":
            resolver_transcript = CANONICAL_TRANSCRIPTS.get(normalized_gene)
            if resolver_transcript is not None:
                provenance.append("local_canonical_transcript_map")
            else:
                resolver_transcript, resolver_warnings = self._resolve_mane_transcript(
                    normalized_gene,
                    deadline=deadline,
                )
                warnings.extend(resolver_warnings)
                if resolver_transcript is not None:
                    provenance.append("ensembl_mane_transcript_lookup")

        resolver_transcript_hgvs = (
            f"{resolver_transcript}:{hgvs}" if resolver_transcript else transcript_hgvs
        )
        genomic_hg38 = parse_genomic_variant_id(hgvs) if kind == "genomic" else None
        genomic_hgvs = hgvs if kind == "genomic" and hgvs.upper().startswith("NC_") else None
        variant_validator_summary = None
        variant_validator_raw = None
        variant_validator_url = None
        local_coordinate_summary = None
        rsid_candidates: tuple[RsidResolutionCandidate, ...] = ()

        if genomic_hg38 is not None:
            if genomic_hgvs is None:
                genomic_hgvs = genomic_variant_id_to_refseq_hgvs(genomic_hg38)
            provenance.append("submitted_genomic_variant_id")
        elif kind == "rsid":
            rsid_candidates, rsid_warnings, rsid_provenance = self._resolve_rsid_candidates(
                hgvs,
                deadline=deadline,
            )
            warnings.extend(rsid_warnings)
            provenance.extend(rsid_provenance)
        elif self.resolve_coordinates and kind == "cdna" and resolver_transcript is not None:
            local_coordinate = self._resolve_eamos_local_coordinates(
                gene=normalized_gene,
                cdna=hgvs,
                transcript=resolver_transcript,
            )
            if local_coordinate is not None:
                genomic_hg38 = local_coordinate.genomic_hg38
                genomic_hgvs = local_coordinate.genomic_hgvs
                local_coordinate_summary = _local_coordinate_summary(local_coordinate)
                warnings.extend(local_coordinate.warnings)
                provenance.append("eamos_local_coordinate_resolver")
            else:
                (
                    genomic_hg38,
                    genomic_hgvs,
                    variant_validator_summary,
                    variant_validator_raw,
                    variant_validator_url,
                    coordinate_warnings,
                ) = self._resolve_variant_validator_coordinates(
                    resolver_transcript_hgvs,
                    deadline=deadline,
                )
                warnings.extend(coordinate_warnings)
                if genomic_hg38 is None:
                    warnings.append("eamos_local_coordinate_unresolved")
            if genomic_hg38 is not None:
                if variant_validator_summary is not None:
                    provenance.append("variant_validator_grch38_vcf")

        source_inputs = SourceSpecificInputs(
            variant_validator=(
                resolver_transcript_hgvs
                if kind == "cdna" and resolver_transcript is not None
                else genomic_hgvs
            ),
            ensembl_vep=(
                resolver_transcript_hgvs
                if kind == "cdna" and resolver_transcript is not None
                else genomic_hgvs
            ),
            gnomad=genomic_hg38,
            spliceai=genomic_hg38,
            clinvar=self._clinvar_input(
                normalized_gene,
                hgvs,
                kind,
                genomic_hgvs,
                resolver_transcript_hgvs if resolver_transcript is not None else None,
            ),
            literature_terms=self._literature_terms(
                normalized_gene,
                hgvs,
                resolver_transcript_hgvs,
                genomic_hg38,
                protein_change,
            ),
        )
        audit = _coordinate_resolution_audit(
            kind=kind,
            coordinate_resolution_requested=self.resolve_coordinates,
            genomic_hg38=genomic_hg38,
            genomic_hgvs=genomic_hgvs,
            source_inputs=source_inputs,
            provenance=tuple(provenance),
            warnings=tuple(warnings),
            local_coordinate_summary=local_coordinate_summary,
            variant_validator_summary=variant_validator_summary,
            variant_validator_url=variant_validator_url,
            rsid_candidates=rsid_candidates,
        )

        return SearchInputResolution(
            gene=normalized_gene,
            hgvs=hgvs,
            transcript=normalized_transcript,
            protein_change=protein_change,
            kind=kind,
            transcript_hgvs=transcript_hgvs,
            resolver_transcript=resolver_transcript,
            resolver_transcript_hgvs=resolver_transcript_hgvs,
            genomic_hg38=genomic_hg38,
            genomic_hgvs=genomic_hgvs,
            source_inputs=source_inputs,
            warnings=tuple(warnings),
            provenance=tuple(provenance),
            variant_validator_summary=variant_validator_summary,
            variant_validator_raw=variant_validator_raw,
            variant_validator_url=variant_validator_url,
            local_coordinate_summary=local_coordinate_summary,
            coordinate_resolution_audit=audit,
            rsid_candidates=rsid_candidates,
        )

    def _resolve_eamos_local_coordinates(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str,
    ) -> EamosCoordinateResolution | None:
        resolver = self._local_coordinate_resolver
        if resolver is None:
            resolver = build_runtime_coordinate_resolver(self.settings)
            self._local_coordinate_resolver = resolver
        return resolver.resolve(gene=gene, cdna=cdna, transcript=transcript)

    def _resolve_mane_transcript(
        self,
        gene: str,
        *,
        deadline: float,
    ) -> tuple[str | None, list[str]]:
        if self.settings is None or not getattr(self.settings, "use_real_apis", False):
            return None, []

        url = (
            f"{self.settings.vep_base_url}/lookup/symbol/homo_sapiens/"
            f"{quote(gene, safe='')}?expand=1;mane=1;utr=1"
        )
        try:
            response = httpx.get(
                url,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=self._http_timeout_seconds(deadline),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return None, [f"transcript_resolution_failed:{type(exc).__name__}"]

        transcripts = [
            transcript
            for transcript in _as_list(
                payload.get("Transcript") if isinstance(payload, dict) else None
            )
            if isinstance(transcript, dict)
        ]
        for transcript in transcripts:
            if transcript.get("biotype") != "protein_coding":
                continue
            for mane in _as_list(transcript.get("MANE")):
                if not isinstance(mane, dict) or mane.get("type") != "MANE_Select":
                    continue
                refseq_match = str(mane.get("refseq_match") or "").strip()
                if refseq_match:
                    return refseq_match, []

        canonical = (
            str(payload.get("canonical_transcript") or "") if isinstance(payload, dict) else ""
        )
        for transcript in transcripts:
            if transcript.get("biotype") != "protein_coding":
                continue
            if canonical and str(transcript.get("id") or "") == canonical:
                resolved = _versioned_ensembl_id(transcript)
                if resolved:
                    return resolved, []

        for transcript in transcripts:
            if transcript.get("biotype") != "protein_coding" or transcript.get("is_canonical") != 1:
                continue
            resolved = _versioned_ensembl_id(transcript)
            if resolved:
                return resolved, []

        return None, [f"transcript_resolution_unavailable:{gene}"]

    def _resolve_variant_validator_coordinates(
        self,
        transcript_hgvs: str,
        *,
        deadline: float,
    ) -> tuple[
        str | None, str | None, dict[str, Any] | None, dict[str, Any] | None, str | None, list[str]
    ]:
        if self.settings is None or not getattr(self.settings, "use_real_apis", False):
            return None, None, None, None, None, []

        url = (
            f"{self.settings.variant_validator_base_url}"
            f"/VariantValidator/variantvalidator/GRCh38/{quote(transcript_hgvs, safe='')}/all"
        )
        try:
            response = httpx.get(url, timeout=self._http_timeout_seconds(deadline))
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return (
                None,
                None,
                None,
                None,
                url,
                [f"coordinate_resolution_failed:{type(exc).__name__}"],
            )

        summary = _variant_validator_summary(payload)
        return (
            summary.get("variant_id"),
            summary.get("hgvs_genomic_description"),
            summary,
            payload,
            url,
            [],
        )

    def _resolve_rsid_candidates(
        self,
        rsid: str,
        *,
        deadline: float,
    ) -> tuple[tuple[RsidResolutionCandidate, ...], list[str], list[str]]:
        fixture_candidates = _fixture_rsid_candidates(rsid)
        if self.settings is None or not getattr(self.settings, "use_real_apis", False):
            if fixture_candidates:
                return fixture_candidates, [], ["rsid_resolution_fixture"]
            return (), [], []

        url = f"{self.settings.vep_base_url}" f"/vep/human/id/{quote(rsid, safe='')}"
        try:
            response = httpx.get(
                url,
                params={
                    "content-type": "application/json",
                    "hgvs": "1",
                    "canonical": "1",
                    "mane": "1",
                },
                headers={"Accept": "application/json"},
                timeout=self._http_timeout_seconds(deadline),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            warnings = [f"rsid_resolution_failed:{type(exc).__name__}"]
            if fixture_candidates:
                return fixture_candidates, warnings, ["rsid_resolution_fixture"]
            return (), warnings, []

        candidate_payload = payload[0] if isinstance(payload, list) and payload else {}
        if not isinstance(candidate_payload, dict):
            return (), [f"rsid_resolution_unavailable:{rsid}"], ["ensembl_vep_rsid_lookup"]

        candidates = _rsid_candidates_from_vep_payload(rsid, candidate_payload)
        warnings: list[str] = []
        if not candidates:
            warnings.append(f"rsid_resolution_unavailable:{rsid}")
        return candidates, warnings, ["ensembl_vep_rsid_lookup"]

    def _http_timeout_seconds(self, deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("search input resolver deadline exceeded")
        return min(self.timeout_seconds, max(0.001, remaining))

    def _clinvar_input(
        self,
        gene: str,
        hgvs: str,
        kind: QueryKind,
        genomic_hgvs: str | None,
        resolver_transcript_hgvs: str | None,
    ) -> str | None:
        if genomic_hgvs:
            return genomic_hgvs
        if kind == "cdna":
            return resolver_transcript_hgvs or f"{gene}:{hgvs}"
        if kind == "rsid":
            return hgvs
        if kind == "genomic":
            return genomic_hgvs or parse_genomic_variant_id(hgvs) or hgvs
        return None

    def _literature_terms(
        self,
        gene: str,
        hgvs: str,
        transcript_hgvs: str,
        genomic_hg38: str | None,
        protein_change: str | None,
    ) -> tuple[str, ...]:
        terms = [gene, hgvs, transcript_hgvs, genomic_hg38, protein_change]
        unique: list[str] = []
        for term in terms:
            if term and term not in unique:
                unique.append(term)
        return tuple(unique)


@lru_cache(maxsize=1)
def _rsid_resolution_fixture() -> tuple[dict[str, Any], ...]:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "rsid_resolution_records.json"
    if not fixture_path.exists():
        return ()
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return tuple(item for item in payload if isinstance(item, dict))


def _fixture_rsid_candidates(rsid: str) -> tuple[RsidResolutionCandidate, ...]:
    normalized = rsid.strip().lower()
    candidates = [
        _rsid_candidate_from_mapping(item)
        for item in _rsid_resolution_fixture()
        if str(item.get("rsid") or "").strip().lower() == normalized
    ]
    return tuple(candidate for candidate in candidates if candidate is not None)


def _rsid_candidate_from_mapping(item: dict[str, Any]) -> RsidResolutionCandidate | None:
    rsid = str(item.get("rsid") or "").strip()
    gene = str(item.get("gene") or "").strip().upper()
    cdna = str(item.get("cdna") or "").strip()
    if not (rsid and gene and cdna):
        return None
    transcript = _optional_text(item.get("transcript"))
    protein_change = _optional_text(item.get("protein_change"))
    genomic_hg38 = _optional_text(item.get("genomic_hg38"))
    genomic_hgvs = _optional_text(item.get("genomic_hgvs"))
    source_support = tuple(
        str(value).strip() for value in item.get("source_support") or [] if str(value).strip()
    )
    return RsidResolutionCandidate(
        candidate_id=str(
            item.get("candidate_id") or _rsid_candidate_id(rsid, gene, transcript, cdna)
        ),
        display_label=str(
            item.get("display_label") or _rsid_display_label(gene, transcript, cdna, protein_change)
        ),
        rsid=rsid,
        gene=gene,
        cdna=cdna,
        transcript=transcript,
        protein_change=protein_change,
        genomic_hg38=genomic_hg38,
        genomic_hgvs=genomic_hgvs,
        variant_allele=_optional_text(item.get("variant_allele")),
        source_support=source_support,
        is_preferred=bool(item.get("is_preferred", False)),
    )


def _rsid_candidates_from_vep_payload(
    rsid: str,
    payload: dict[str, Any],
) -> tuple[RsidResolutionCandidate, ...]:
    supported_alleles = _source_supported_alleles(payload, rsid)
    ranked: list[tuple[int, RsidResolutionCandidate]] = []
    seen: set[tuple[str, str | None, str, str | None]] = set()
    for consequence in _as_list(payload.get("transcript_consequences")):
        if not isinstance(consequence, dict):
            continue
        gene = str(consequence.get("gene_symbol") or "").strip().upper()
        hgvsc = str(consequence.get("hgvsc") or "").strip()
        transcript_from_hgvsc, cdna = _split_hgvsc(hgvsc)
        if not (gene and cdna):
            continue
        transcript = _optional_text(consequence.get("mane_select")) or transcript_from_hgvsc
        if not transcript:
            continue
        variant_allele = _optional_text(consequence.get("variant_allele"))
        genomic_hg38 = _variant_id_from_vep_payload(payload, variant_allele)
        genomic_hgvs = genomic_variant_id_to_refseq_hgvs(genomic_hg38) if genomic_hg38 else None
        protein_change = _protein_change_from_hgvsp(consequence.get("hgvsp"))
        support = ["Ensembl VEP rsID"]
        if consequence.get("mane_select"):
            support.append("MANE Select")
        if consequence.get("canonical") in {1, "1", True}:
            support.append("canonical transcript")
        if variant_allele and variant_allele.upper() in supported_alleles:
            support.append("source-supported alternate allele")
        key = (gene, transcript, cdna, variant_allele)
        if key in seen:
            continue
        seen.add(key)
        candidate = RsidResolutionCandidate(
            candidate_id=_rsid_candidate_id(rsid, gene, transcript, cdna),
            display_label=_rsid_display_label(gene, transcript, cdna, protein_change),
            rsid=rsid,
            gene=gene,
            cdna=cdna,
            transcript=transcript,
            protein_change=protein_change,
            genomic_hg38=genomic_hg38,
            genomic_hgvs=genomic_hgvs,
            variant_allele=variant_allele,
            source_support=tuple(support),
            is_preferred=False,
        )
        ranked.append(
            (_rsid_candidate_score(consequence, variant_allele, supported_alleles), candidate)
        )

    candidates = [
        candidate for _, candidate in sorted(ranked, key=lambda item: item[0], reverse=True)
    ]
    candidates = _prefer_best_transcript_set(candidates)
    preferred_indexes = [
        index
        for index, candidate in enumerate(candidates)
        if candidate.variant_allele and candidate.variant_allele.upper() in supported_alleles
    ]
    if len(candidates) == 1:
        preferred_indexes = [0]
    elif len(preferred_indexes) != 1:
        preferred_indexes = []
    return tuple(
        replace(candidate, is_preferred=index in preferred_indexes)
        for index, candidate in enumerate(candidates)
    )


def _source_supported_alleles(payload: dict[str, Any], rsid: str) -> set[str]:
    supported: set[str] = set()
    for colocated in _as_list(payload.get("colocated_variants")):
        if not isinstance(colocated, dict):
            continue
        if str(colocated.get("id") or "").lower() != rsid.lower():
            continue
        frequencies = colocated.get("frequencies")
        if isinstance(frequencies, dict):
            supported.update(str(allele).upper() for allele in frequencies if str(allele).strip())
        clin_sig_allele = str(colocated.get("clin_sig_allele") or "")
        for token in re.split(r"[;,\s]+", clin_sig_allele):
            allele = token.split(":", 1)[0].strip().upper()
            if allele:
                supported.add(allele)
    return supported


def _variant_id_from_vep_payload(payload: dict[str, Any], variant_allele: str | None) -> str | None:
    chrom = str(payload.get("seq_region_name") or "").removeprefix("chr")
    pos = str(payload.get("start") or "")
    allele_string = str(payload.get("allele_string") or "")
    alleles = [part.upper() for part in allele_string.split("/") if part and part != "-"]
    if not (chrom and pos and variant_allele and alleles):
        return None
    ref = alleles[0]
    alt = variant_allele.upper()
    if not re.fullmatch(r"[ACGT]+", ref) or not re.fullmatch(r"[ACGT]+", alt):
        return None
    return f"{chrom}-{pos}-{ref}-{alt}"


def _split_hgvsc(hgvsc: str) -> tuple[str | None, str | None]:
    if ":" not in hgvsc:
        return None, None
    transcript, cdna = hgvsc.split(":", 1)
    cdna = cdna.strip()
    return transcript.strip() or None, cdna or None


def _protein_change_from_hgvsp(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text.split(":", 1)[-1]


def _rsid_candidate_score(
    consequence: dict[str, Any],
    variant_allele: str | None,
    supported_alleles: set[str],
) -> int:
    score = 0
    if consequence.get("mane_select"):
        score += 100
    if consequence.get("canonical") in {1, "1", True}:
        score += 50
    if str(consequence.get("biotype") or "") == "protein_coding":
        score += 20
    if consequence.get("hgvsc"):
        score += 10
    if consequence.get("hgvsp"):
        score += 5
    if variant_allele and variant_allele.upper() in supported_alleles:
        score += 40
    return score


def _prefer_best_transcript_set(
    candidates: list[RsidResolutionCandidate],
) -> list[RsidResolutionCandidate]:
    if any("MANE Select" in candidate.source_support for candidate in candidates):
        candidates = [
            candidate for candidate in candidates if "MANE Select" in candidate.source_support
        ]
    elif any("canonical transcript" in candidate.source_support for candidate in candidates):
        candidates = [
            candidate
            for candidate in candidates
            if "canonical transcript" in candidate.source_support
        ]
    return candidates[:6]


def _rsid_candidate_id(
    rsid: str,
    gene: str,
    transcript: str | None,
    cdna: str,
) -> str:
    token = "_".join(part for part in (gene, transcript or "", cdna) if part)
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", token).strip("_")
    return f"ensembl:{rsid}:{token}"


def _rsid_display_label(
    gene: str,
    transcript: str | None,
    cdna: str,
    protein_change: str | None,
) -> str:
    label = f"{gene} {transcript + ':' if transcript else ''}{cdna}"
    if protein_change:
        label += f" ({protein_change})"
    return label


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


_TRANSCRIPT_SEARCH_RE = re.compile(
    r"^(?P<transcript>(?:N[MR]_|ENST)[A-Z0-9_.]+)"
    r"(?:\((?P<gene>[A-Z][A-Z0-9-]*)\))?:"
    r"(?P<hgvs>.+)$",
    flags=re.IGNORECASE,
)
_GENE_TRANSCRIPT_SEARCH_RE = re.compile(
    r"^(?P<gene>[A-Z][A-Z0-9-]*)\s+"
    r"(?P<transcript>(?:N[MR]_|ENST)[A-Z0-9_.]+):"
    r"(?P<hgvs>.+)$",
    flags=re.IGNORECASE,
)
_GENE_PREFIX_SEARCH_RE = re.compile(
    r"^(?P<gene>[A-Z][A-Z0-9-]*)\s*:\s*" r"(?P<hgvs>(?:[CGMNP]\..+|rs\d+))$",
    flags=re.IGNORECASE,
)
_GENE_SPACE_SEARCH_RE = re.compile(
    r"^(?P<gene>[A-Z][A-Z0-9-]*)\s+" r"(?P<hgvs>(?:[CGMNP]\..+|rs\d+))$",
    flags=re.IGNORECASE,
)
_TRAILING_PROTEIN_RE = re.compile(r"\s*\((?P<protein>p\.[^)]+)\)\s*$", flags=re.IGNORECASE)


def parse_search_text(
    text: str,
    *,
    gene: str | None = None,
    transcript: str | None = None,
    protein_change: str | None = None,
) -> ParsedSearchInput:
    """Parse a search-box style string into resolver inputs."""
    submitted_text = text
    working = text.strip()
    warnings: list[str] = []

    protein_match = _TRAILING_PROTEIN_RE.search(working)
    if protein_match is not None:
        protein_change = protein_change or protein_match.group("protein")
        working = working[: protein_match.start()].strip()

    parsed_gene = (gene or "").strip()
    parsed_transcript = transcript.strip() if transcript else None
    parsed_cdna = working

    transcript_match = _TRANSCRIPT_SEARCH_RE.fullmatch(working)
    if transcript_match is not None:
        parsed_transcript = parsed_transcript or transcript_match.group("transcript")
        parsed_gene = parsed_gene or transcript_match.group("gene") or ""
        parsed_cdna = transcript_match.group("hgvs")
    else:
        gene_transcript_match = _GENE_TRANSCRIPT_SEARCH_RE.fullmatch(working)
        if gene_transcript_match is not None:
            parsed_gene = parsed_gene or gene_transcript_match.group("gene")
            parsed_transcript = parsed_transcript or gene_transcript_match.group("transcript")
            parsed_cdna = gene_transcript_match.group("hgvs")
        else:
            gene_prefix_match = _GENE_PREFIX_SEARCH_RE.fullmatch(working)
            if gene_prefix_match is not None:
                parsed_gene = parsed_gene or gene_prefix_match.group("gene")
                parsed_cdna = gene_prefix_match.group("hgvs")
            else:
                gene_space_match = _GENE_SPACE_SEARCH_RE.fullmatch(working)
                if gene_space_match is not None:
                    parsed_gene = parsed_gene or gene_space_match.group("gene")
                    parsed_cdna = gene_space_match.group("hgvs")

    normalized_gene, _, _, kind = normalize_variant_query(
        parsed_gene,
        parsed_cdna,
        parsed_transcript,
    )
    if not normalized_gene and kind in {"cdna", "protein"}:
        warnings.append("gene_missing_for_gene_specific_variant_input")

    return ParsedSearchInput(
        submitted_text=submitted_text,
        gene=parsed_gene,
        cdna=parsed_cdna,
        transcript=parsed_transcript,
        protein_change=protein_change,
        warnings=tuple(warnings),
    )


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _versioned_ensembl_id(transcript: dict[str, Any]) -> str:
    transcript_id = str(transcript.get("id") or "")
    version = transcript.get("version")
    if transcript_id and version:
        return f"{transcript_id}.{version}"
    return transcript_id


def _vcf_to_variant_id(vcf: dict[str, Any] | None) -> str | None:
    if not vcf:
        return None
    chrom = str(vcf.get("chr") or "").removeprefix("chr")
    pos = str(vcf.get("pos") or "")
    ref = str(vcf.get("ref") or "").upper()
    alt = str(vcf.get("alt") or "").upper()
    if not all((chrom, pos, ref, alt)):
        return None
    return f"{chrom}-{pos}-{ref}-{alt}"


def _variant_validator_summary(payload: dict[str, Any]) -> dict[str, Any]:
    variant_payload = next(
        (
            value
            for key, value in payload.items()
            if key not in {"flag", "metadata"} and isinstance(value, dict)
        ),
        {},
    )
    loci = variant_payload.get("primary_assembly_loci", {})
    grch38 = loci.get("grch38", {}) if isinstance(loci, dict) else {}
    vcf = grch38.get("vcf") or {} if isinstance(grch38, dict) else {}
    return {
        "gene": variant_payload.get("gene_symbol"),
        "submitted_variant": variant_payload.get("submitted_variant"),
        "hgvs_transcript_variant": variant_payload.get("hgvs_transcript_variant"),
        "hgvs_genomic_description": grch38.get("hgvs_genomic_description"),
        "vcf": {
            "chr": str(vcf.get("chr") or "").removeprefix("chr"),
            "pos": str(vcf.get("pos") or ""),
            "ref": str(vcf.get("ref") or "").upper(),
            "alt": str(vcf.get("alt") or "").upper(),
        },
        "variant_id": _vcf_to_variant_id(vcf),
        "exon": _exon_from_variant_validator_payload(variant_payload),
        "selected_assembly": variant_payload.get("selected_assembly"),
    }


def _local_coordinate_summary(resolution: EamosCoordinateResolution) -> dict[str, Any]:
    return {
        "gene": resolution.gene,
        "hgvs_transcript_variant": f"{resolution.transcript}:{resolution.cdna}",
        "hgvs_genomic_description": resolution.genomic_hgvs,
        "vcf": {
            "chr": resolution.chrom,
            "pos": str(resolution.pos),
            "ref": resolution.ref,
            "alt": resolution.alt,
        },
        "variant_id": resolution.genomic_hg38,
        "source": resolution.source,
        "confidence": resolution.confidence,
        "provenance": list(resolution.provenance),
    }


def _local_coordinate_resolver_settings(settings) -> dict[str, Any]:
    if settings is None:
        return {
            "compact_index_path": DEFAULT_COMPACT_COORDINATE_INDEX_PATH,
            "mane_gff_path": None,
            "refseq_gff_path": None,
        }

    compact_index_path = _settings_path(
        settings,
        getattr(settings, "coordinate_resolver_compact_index_path", None),
    )
    reference_path = _settings_path(
        settings,
        getattr(settings, "coordinate_resolver_hg38_2bit_path", None)
        or getattr(settings, "hg38_2bit_runtime_asset_path", None),
    )
    kwargs: dict[str, Any] = {
        "compact_index_path": compact_index_path,
        "mane_gff_path": None,
        "refseq_gff_path": None,
    }
    if reference_path is not None:
        kwargs["reference_store_factory"] = lambda path=reference_path: TwoBitReferenceGenomeStore(
            path,
            source_version="UCSC hg38.2bit",
            verify_checksum=False,
        )
    return kwargs


def build_runtime_coordinate_resolver(settings) -> EamosLocalCoordinateResolver:
    """Build the runtime coordinate resolver without raw GFF scan paths."""
    return EamosLocalCoordinateResolver(**_local_coordinate_resolver_settings(settings))


def _settings_path(settings, path: Path | str | None) -> Path | None:
    if path is None:
        return None
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    backend_root = getattr(settings, "backend_root", None)
    if backend_root is None:
        return resolved
    return Path(backend_root) / resolved


def _coordinate_resolution_audit(
    *,
    kind: QueryKind,
    coordinate_resolution_requested: bool,
    genomic_hg38: str | None,
    genomic_hgvs: str | None,
    source_inputs: SourceSpecificInputs,
    provenance: tuple[str, ...],
    warnings: tuple[str, ...],
    local_coordinate_summary: dict[str, Any] | None,
    variant_validator_summary: dict[str, Any] | None,
    variant_validator_url: str | None,
    rsid_candidates: tuple[RsidResolutionCandidate, ...],
) -> CoordinateResolutionAudit:
    used_submitted_genomic = "submitted_genomic_variant_id" in provenance
    used_eamos_local = local_coordinate_summary is not None
    used_variant_validator = variant_validator_summary is not None
    used_rsid_candidates = bool(rsid_candidates)
    used_clinvar_for_coordinates = False

    if used_submitted_genomic:
        resolver_path = "submitted_genomic"
    elif used_eamos_local:
        resolver_path = "eamos_local"
    elif used_variant_validator:
        resolver_path = "variant_validator_fallback"
    elif used_rsid_candidates:
        resolver_path = "rsid_candidates"
    elif coordinate_resolution_requested and kind == "cdna":
        resolver_path = "unresolved"
    elif kind == "cdna":
        resolver_path = "not_requested"
    else:
        resolver_path = "not_applicable"

    clinvar_role = None
    if source_inputs.clinvar:
        clinvar_role = "source_query_input_not_coordinate_provider"

    return CoordinateResolutionAudit(
        resolver_path=resolver_path,
        coordinate_resolution_requested=coordinate_resolution_requested,
        used_eamos_local=used_eamos_local,
        used_variant_validator=used_variant_validator,
        used_clinvar_for_coordinates=used_clinvar_for_coordinates,
        used_submitted_genomic=used_submitted_genomic,
        used_rsid_candidates=used_rsid_candidates,
        canonical_variant_id=genomic_hg38,
        genomic_hgvs=genomic_hgvs,
        local_source=(
            str(local_coordinate_summary.get("source"))
            if local_coordinate_summary and local_coordinate_summary.get("source")
            else None
        ),
        variant_validator_url=variant_validator_url,
        clinvar_role=clinvar_role,
        provenance=provenance,
        warnings=warnings,
    )


def _exon_from_variant_validator_payload(variant_payload: dict[str, Any]) -> str | None:
    positions = variant_payload.get("variant_exonic_positions")
    if not isinstance(positions, dict):
        return None
    for accession in ("NC_000001.11", "GRCh38", "grch38", "hg38", "NG_008472.2"):
        exon = _format_exon(positions.get(accession))
        if exon:
            return exon
    for value in positions.values():
        exon = _format_exon(value)
        if exon:
            return exon
    return None


def _format_exon(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    start = str(value.get("start_exon") or "").strip()
    end = str(value.get("end_exon") or "").strip()
    if not start and not end:
        return None
    if start and end and start != end:
        return f"{start}-{end}"
    return start or end


def _positive_float(value, *, default: float) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default
