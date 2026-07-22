from __future__ import annotations

import json
import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Callable, Literal, Protocol
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.data_sources.runtime_assets import (
    ResolvedRuntimeAsset,
    SourceAssetMaterializationError,
    SourceAssetMaterializationStore,
    resolve_hg38_materialized_runtime_asset,
)
from app.services.reference_genome import (
    ReferenceGenomeStoreError,
    ReferenceWindow,
    TwoBitReferenceGenomeStore,
)

CANONICAL_TRANSCRIPTS: dict[str, str] = {
    "RPE65": "NM_000329.3",
}
NC_CHROMOSOME_ACCESSIONS: dict[str, str] = {
    "NC_000001.11": "1",
    "NC_000002.12": "2",
    "NC_000003.12": "3",
    "NC_000004.12": "4",
    "NC_000005.10": "5",
    "NC_000006.12": "6",
    "NC_000007.14": "7",
    "NC_000008.11": "8",
    "NC_000009.12": "9",
    "NC_000010.11": "10",
    "NC_000011.10": "11",
    "NC_000012.12": "12",
    "NC_000013.11": "13",
    "NC_000014.9": "14",
    "NC_000015.10": "15",
    "NC_000016.10": "16",
    "NC_000017.11": "17",
    "NC_000018.10": "18",
    "NC_000019.10": "19",
    "NC_000020.11": "20",
    "NC_000021.9": "21",
    "NC_000022.11": "22",
    "NC_000023.11": "X",
    "NC_000024.10": "Y",
    "NC_012920.1": "M",
}
CHROMOSOME_NC_ACCESSIONS: dict[str, str] = {
    chrom: accession for accession, chrom in NC_CHROMOSOME_ACCESSIONS.items()
}

WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE = "workbench_sequence_context_unavailable"
# The external coordinate/sequence resolver (VariantValidator / Ensembl) timed out
# or otherwise failed at the transport layer. Distinct from "unavailable" (no data)
# so a transient upstream failure is observable and never 500s the lookup.
WORKBENCH_SEQUENCE_CONTEXT_RESOLVER_ERROR = "workbench_sequence_context_resolver_error"
WORKBENCH_UNSUPPORTED_INPUT_PREFIX = "workbench_unsupported_input"

QueryKind = Literal["cdna", "rsid", "protein", "genomic", "unknown"]
SequenceContextSource = Literal["fixture", "resolver"]
Strand = Literal["+", "-", "unknown"]


def _normalize_variant_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value.strip())

    spaced_vcf = re.fullmatch(
        r"(?:chr)?(?P<chrom>\d+|X|Y|M|MT)\s+" r"(?P<pos>\d+)\s+(?P<ref>[ACGT]+)\s+(?P<alt>[ACGT]+)",
        text,
        flags=re.IGNORECASE,
    )
    if spaced_vcf is not None:
        chrom = spaced_vcf.group("chrom").upper()
        if chrom == "MT":
            chrom = "M"
        return (
            f"{chrom}-{spaced_vcf.group('pos')}-"
            f"{spaced_vcf.group('ref').upper()}-{spaced_vcf.group('alt').upper()}"
        )

    colon_substitution = re.fullmatch(
        r"(?:chr)?(?P<chrom>\d+|X|Y|M|MT):" r"(?P<pos>\d+)\s+(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)",
        text,
        flags=re.IGNORECASE,
    )
    if colon_substitution is not None:
        chrom = colon_substitution.group("chrom").upper()
        if chrom == "MT":
            chrom = "M"
        return (
            f"{chrom}-{colon_substitution.group('pos')}-"
            f"{colon_substitution.group('ref').upper()}-"
            f"{colon_substitution.group('alt').upper()}"
        )

    delimited_vcf = re.fullmatch(
        r"(?:chr)?(?P<chrom>\d+|X|Y|M|MT)[:-]"
        r"(?P<pos>\d+)[:-](?P<ref>[ACGT]+)[:-](?P<alt>[ACGT]+)",
        text,
        flags=re.IGNORECASE,
    )
    if delimited_vcf is not None:
        chrom = delimited_vcf.group("chrom").upper()
        if chrom == "MT":
            chrom = "M"
        return (
            f"{chrom}-{delimited_vcf.group('pos')}-"
            f"{delimited_vcf.group('ref').upper()}-{delimited_vcf.group('alt').upper()}"
        )

    return re.sub(r"\s+", "", text)


def normalize_variant_query(
    gene: str,
    cdna: str,
    transcript: str | None,
) -> tuple[str, str, str | None, QueryKind]:
    normalized_gene = gene.strip().upper()
    hgvs = _normalize_variant_text(cdna)
    normalized_transcript = transcript.strip() if transcript else None

    if ":" in hgvs:
        prefix, remainder = hgvs.split(":", 1)
        prefix_upper = prefix.upper()
        if prefix_upper == normalized_gene:
            hgvs = remainder
        elif prefix_upper.startswith(("NM_", "ENST")):
            normalized_transcript = re.sub(r"\([^)]*\)$", "", prefix)
            hgvs = remainder

    hgvs = re.sub(r"\(p\.[^)]+\)$", "", hgvs)

    if re.match(r"^c\.", hgvs):
        kind: QueryKind = "cdna"
    elif re.match(r"^rs\d+$", hgvs, flags=re.IGNORECASE):
        kind = "rsid"
    elif re.match(r"^p\.", hgvs):
        kind = "protein"
    elif re.match(r"^(chr)?[\dXYM]+[:\-]", hgvs, flags=re.IGNORECASE) or re.match(
        r"^NC_\d+\.\d+:", hgvs
    ):
        kind = "genomic"
    else:
        kind = "unknown"

    return normalized_gene, hgvs, normalized_transcript, kind


def parse_genomic_variant_id(hgvs: str) -> str | None:
    """Return gnomAD-style chr-pos-ref-alt for simple genomic SNV/indel input."""
    compact = _normalize_variant_text(hgvs)
    gnomad_match = re.fullmatch(
        r"(?:chr)?(?P<chrom>\d+|X|Y|M|MT)[:-](?P<pos>\d+)[:-](?P<ref>[ACGT]+)[:-](?P<alt>[ACGT]+)",
        compact,
        flags=re.IGNORECASE,
    )
    if gnomad_match is not None:
        chrom = gnomad_match.group("chrom").upper()
        if chrom == "MT":
            chrom = "M"
        return (
            f"{chrom}-{gnomad_match.group('pos')}-"
            f"{gnomad_match.group('ref').upper()}-{gnomad_match.group('alt').upper()}"
        )

    colon_substitution_match = re.fullmatch(
        r"(?:chr)?(?P<chrom>\d+|X|Y|M|MT):" r"(?P<pos>\d+)(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)",
        compact,
        flags=re.IGNORECASE,
    )
    if colon_substitution_match is not None:
        chrom = colon_substitution_match.group("chrom").upper()
        if chrom == "MT":
            chrom = "M"
        return (
            f"{chrom}-{colon_substitution_match.group('pos')}-"
            f"{colon_substitution_match.group('ref').upper()}-"
            f"{colon_substitution_match.group('alt').upper()}"
        )

    nc_match = re.fullmatch(
        r"(?P<accession>NC_\d{6}\.\d+):g\.(?P<pos>\d+)(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)",
        compact,
        flags=re.IGNORECASE,
    )
    if nc_match is None:
        return None
    accession = nc_match.group("accession").upper()
    chrom = NC_CHROMOSOME_ACCESSIONS.get(accession)
    if chrom is None:
        return None
    return (
        f"{chrom}-{nc_match.group('pos')}-"
        f"{nc_match.group('ref').upper()}-{nc_match.group('alt').upper()}"
    )


def genomic_variant_id_to_refseq_hgvs(variant_id: str) -> str | None:
    """Return simple RefSeq genomic HGVS for chr-pos-ref-alt variants on GRCh38."""
    parsed = parse_genomic_variant_id(variant_id)
    if parsed is None:
        return None
    chrom, pos, ref, alt = parsed.split("-", 3)
    accession = CHROMOSOME_NC_ACCESSIONS.get(chrom)
    if accession is None:
        return None

    pos_int = int(pos)
    if len(ref) == 1 and len(alt) == 1:
        return f"{accession}:g.{pos}{ref}>{alt}"

    if len(alt) > len(ref) and alt.startswith(ref):
        inserted = alt[len(ref) :]
        if not inserted:
            return None
        return f"{accession}:g.{pos_int}_{pos_int + 1}ins{inserted}"

    if len(ref) > len(alt) and ref.startswith(alt):
        deleted = ref[len(alt) :]
        if not deleted:
            return None
        start = pos_int + len(alt)
        end = start + len(deleted) - 1
        if start == end:
            return f"{accession}:g.{start}del{deleted}"
        return f"{accession}:g.{start}_{end}del{deleted}"

    if len(ref) == len(alt) and len(ref) > 1:
        end = pos_int + len(ref) - 1
        return f"{accession}:g.{pos_int}_{end}delins{alt}"

    return None


def unsupported_input_warning(kind: str) -> str:
    return f"{WORKBENCH_UNSUPPORTED_INPUT_PREFIX}:{kind}"


class NormalizedVariantQuery(BaseModel):
    gene: str
    hgvs: str
    transcript: str | None = None
    kind: QueryKind
    transcript_hgvs: str
    resolver_transcript: str | None = None
    resolver_transcript_hgvs: str


def normalize_sequence_query(
    gene: str,
    cdna: str,
    transcript: str | None = None,
) -> NormalizedVariantQuery:
    normalized_gene, hgvs, normalized_transcript, kind = normalize_variant_query(
        gene,
        cdna,
        transcript,
    )
    transcript_hgvs = f"{normalized_transcript}:{hgvs}" if normalized_transcript else hgvs
    resolver_transcript = normalized_transcript
    if resolver_transcript is None and kind == "cdna":
        resolver_transcript = CANONICAL_TRANSCRIPTS.get(normalized_gene)
    resolver_transcript_hgvs = (
        f"{resolver_transcript}:{hgvs}" if resolver_transcript else transcript_hgvs
    )
    return NormalizedVariantQuery(
        gene=normalized_gene,
        hgvs=hgvs,
        transcript=normalized_transcript,
        kind=kind,
        transcript_hgvs=transcript_hgvs,
        resolver_transcript=resolver_transcript,
        resolver_transcript_hgvs=resolver_transcript_hgvs,
    )


class SequenceContext(BaseModel):
    gene: str
    cdna: str
    transcript: str | None = None
    transcript_hgvs: str
    query_kind: QueryKind
    species: str = "human"
    genome_build: str = "GRCh38"
    genomic_hg38: str | None = None
    strand: Strand = "unknown"
    window_sequence: str
    target_offset: int
    reference_base: str | None = None
    alternate_base: str | None = None
    codon_number: int | None = None
    codon_ref: str | None = None
    codon_alt: str | None = None
    source: SequenceContextSource
    source_metadata: dict[str, str] = Field(default_factory=dict)
    # Internal request-lifetime mapping used by Workbench Context V2 engines.
    # ``None`` marks an inserted base that has no GRCh38 coordinate. Ordinary
    # resolver contexts omit the field and retain their historical shape.
    genomic_coordinates: tuple[int | None, ...] | None = None
    warnings: list[str] = Field(default_factory=list)


class SequenceContextResult(BaseModel):
    query: NormalizedVariantQuery
    context: SequenceContext | None = None
    warnings: list[str] = Field(default_factory=list)


class SequenceContextResolver(Protocol):
    def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext | None:
        """Return a source-backed sequence context for a normalized query."""


class ReferenceSequenceReader(Protocol):
    def get_sequence(
        self,
        chrom: str,
        start: int,
        end: int,
        build: str | None = None,
    ) -> ReferenceWindow: ...


class EnsemblVariantSequenceResolver:
    """Resolve a cDNA variant to a GRCh38 sequence window for local design engines."""

    def __init__(
        self,
        settings: Settings,
        *,
        flank_bp: int = 1000,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.settings = settings
        self.flank_bp = flank_bp
        self.timeout_seconds = timeout_seconds

    def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext | None:
        if species != "human" or query.kind != "cdna" or not query.resolver_transcript_hgvs:
            return None

        summary = self._variant_validator_summary(query)
        vcf = summary.get("vcf") if isinstance(summary, dict) else None
        if not isinstance(vcf, dict):
            return None

        chrom = str(vcf.get("chr") or "").removeprefix("chr")
        pos_text = str(vcf.get("pos") or "")
        ref = str(vcf.get("ref") or "").upper()
        alt = str(vcf.get("alt") or "").upper()
        if not chrom or not pos_text.isdigit() or not ref or not alt:
            return None

        pos = int(pos_text)
        start = max(1, pos - self.flank_bp)
        end = pos + self.flank_bp
        sequence, sequence_url = self._ensembl_sequence(chrom=chrom, start=start, end=end)
        target_offset = pos - start

        return SequenceContext(
            gene=query.gene,
            cdna=query.hgvs,
            transcript=query.resolver_transcript,
            transcript_hgvs=query.resolver_transcript_hgvs,
            query_kind=query.kind,
            species=species,
            genome_build="GRCh38",
            genomic_hg38=f"{chrom}-{pos}-{ref}-{alt}",
            strand="unknown",
            window_sequence=sequence,
            target_offset=target_offset,
            reference_base=ref,
            alternate_base=alt,
            source="resolver",
            source_metadata={
                "coordinate_source": "variant_validator",
                "sequence_source": "ensembl_rest",
                "variant_validator_url": self._variant_validator_url(query),
                "ensembl_sequence_url": sequence_url,
            },
        )

    def _variant_validator_url(self, query: NormalizedVariantQuery) -> str:
        encoded_query = quote(query.resolver_transcript_hgvs, safe="")
        return (
            f"{self.settings.variant_validator_base_url}"
            f"/VariantValidator/variantvalidator/GRCh38/{encoded_query}/all"
        )

    def _variant_validator_summary(self, query: NormalizedVariantQuery) -> dict[str, object]:
        response = httpx.get(self._variant_validator_url(query), timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
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
            "vcf": {
                "chr": str(vcf.get("chr") or "").removeprefix("chr"),
                "pos": str(vcf.get("pos") or ""),
                "ref": str(vcf.get("ref") or ""),
                "alt": str(vcf.get("alt") or ""),
            },
        }

    def _ensembl_sequence(self, *, chrom: str, start: int, end: int) -> tuple[str, str]:
        region = f"{chrom}:{start}..{end}:1"
        url = f"{self.settings.vep_base_url}/sequence/region/human/{region}"
        response = httpx.get(
            url,
            headers={"Content-Type": "text/plain", "Accept": "text/plain"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        sequence = re.sub(r"[^ACGTNacgtn]", "", response.text).upper()
        if not sequence:
            return "", url
        return sequence, url


def _materialized_hg38_reference_store(
    resolved: ResolvedRuntimeAsset,
) -> TwoBitReferenceGenomeStore:
    return TwoBitReferenceGenomeStore(
        resolved.path,
        source_id=resolved.source_id,
        expected_size_bytes=resolved.byte_size,
        expected_md5=resolved.checksum_value,
        verify_checksum=False,
    )


class MaterializedHg38SequenceResolver:
    """Resolve cDNA coordinates, then read the requested window from private hg38.2bit."""

    def __init__(
        self,
        settings: Settings,
        materialization_store: SourceAssetMaterializationStore,
        *,
        flank_bp: int = 1000,
        timeout_seconds: float = 15.0,
        reference_store_factory: (
            Callable[[ResolvedRuntimeAsset], ReferenceSequenceReader] | None
        ) = None,
    ) -> None:
        self.settings = settings
        self.materialization_store = materialization_store
        self.flank_bp = flank_bp
        self.coordinate_resolver = EnsemblVariantSequenceResolver(
            settings,
            flank_bp=flank_bp,
            timeout_seconds=timeout_seconds,
        )
        self.reference_store_factory = reference_store_factory or _materialized_hg38_reference_store
        self._reference_store_lock = threading.RLock()
        self._reference_store_key: tuple[str, str, int | None, str | None] | None = None
        self._reference_store: ReferenceSequenceReader | None = None

    def close(self) -> None:
        with self._reference_store_lock:
            self._close_reference_store_unlocked()

    def _reference_store_for_resolved(
        self,
        resolved: ResolvedRuntimeAsset,
    ) -> ReferenceSequenceReader:
        key = _resolved_asset_store_key(resolved)
        if self._reference_store is None or self._reference_store_key != key:
            self._close_reference_store_unlocked()
            self._reference_store = self.reference_store_factory(resolved)
            self._reference_store_key = key
        return self._reference_store

    def _close_reference_store_unlocked(self) -> None:
        store = self._reference_store
        self._reference_store = None
        self._reference_store_key = None
        close = getattr(store, "close", None)
        if callable(close):
            close()

    def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext | None:
        if species != "human" or query.kind != "cdna" or not query.resolver_transcript_hgvs:
            return None

        summary = self.coordinate_resolver._variant_validator_summary(query)
        vcf = summary.get("vcf") if isinstance(summary, dict) else None
        if not isinstance(vcf, dict):
            return None

        chrom = str(vcf.get("chr") or "").removeprefix("chr")
        pos_text = str(vcf.get("pos") or "")
        ref = str(vcf.get("ref") or "").upper()
        alt = str(vcf.get("alt") or "").upper()
        if not chrom or not pos_text.isdigit() or not ref or not alt:
            return None

        pos = int(pos_text)
        start = max(1, pos - self.flank_bp)
        end = pos + self.flank_bp
        try:
            resolved = resolve_hg38_materialized_runtime_asset(
                self.settings,
                self.materialization_store,
                verify_checksum=False,
            )
            with self._reference_store_lock:
                reference_store = self._reference_store_for_resolved(resolved)
                window = reference_store.get_sequence(chrom, start, end, build="GRCh38")
        except (
            SourceAssetMaterializationError,
            ReferenceGenomeStoreError,
            OSError,
            IndexError,
            ValueError,
        ):
            return None

        return SequenceContext(
            gene=query.gene,
            cdna=query.hgvs,
            transcript=query.resolver_transcript,
            transcript_hgvs=query.resolver_transcript_hgvs,
            query_kind=query.kind,
            species=species,
            genome_build=window.genome_build,
            genomic_hg38=f"{chrom}-{pos}-{ref}-{alt}",
            strand="unknown",
            window_sequence=window.sequence,
            target_offset=pos - start,
            reference_base=ref,
            alternate_base=alt,
            source="resolver",
            source_metadata={
                "coordinate_source": "variant_validator",
                "sequence_source": "ucsc_hg38_2bit_materialized",
                "source_id": resolved.source_id,
                "asset_role": resolved.asset_role,
                "byte_size": str(resolved.byte_size),
                "checksum_algorithm": resolved.checksum_algorithm,
                "checksum_value": resolved.checksum_value,
                "variant_validator_url": self.coordinate_resolver._variant_validator_url(query),
            },
        )


def _resolved_asset_store_key(
    resolved: ResolvedRuntimeAsset,
) -> tuple[str, str, int | None, str | None]:
    return (
        str(getattr(resolved, "path", "")),
        str(getattr(resolved, "source_id", "")),
        getattr(resolved, "byte_size", None),
        getattr(resolved, "checksum_value", None),
    )


@lru_cache(maxsize=1)
def _sequence_context_fixtures() -> dict:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "workbench" / "sequence_contexts.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


class SequenceContextFixtureProvider:
    def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext | None:
        fixture = (
            _sequence_context_fixtures()
            .get(species.lower(), {})
            .get(query.gene, {})
            .get(query.hgvs)
        )
        if not fixture:
            return None
        return SequenceContext(
            **fixture,
            gene=query.gene,
            cdna=query.hgvs,
            transcript=query.resolver_transcript,
            transcript_hgvs=query.resolver_transcript_hgvs,
            query_kind=query.kind,
            species=species.lower(),
            source="fixture",
        )


class SequenceContextService:
    def __init__(
        self,
        settings: Settings | None = None,
        fixture_provider: SequenceContextFixtureProvider | None = None,
        resolver: SequenceContextResolver | None = None,
    ) -> None:
        self.settings = settings
        self.fixture_provider = fixture_provider or SequenceContextFixtureProvider()
        self.resolver = resolver

    def resolve(
        self,
        *,
        gene: str,
        cdna: str,
        transcript: str | None = None,
        species: str = "human",
        prefer_resolver: bool = False,
    ) -> SequenceContextResult:
        normalized_species = species.strip().lower() or "human"
        query = normalize_sequence_query(gene, cdna, transcript)

        if normalized_species != "human":
            return SequenceContextResult(
                query=query,
                warnings=[unsupported_input_warning("species")],
            )

        if query.kind != "cdna":
            return SequenceContextResult(
                query=query,
                warnings=[unsupported_input_warning(query.kind)],
            )

        should_use_resolver = prefer_resolver or (
            self.settings is not None and self.settings.use_real_apis
        )
        if should_use_resolver and self.resolver is not None:
            try:
                context = self.resolver.resolve(query, normalized_species)
            except httpx.HTTPError:
                # VariantValidator / Ensembl timed out or failed at the transport
                # layer. Degrade to a partial section with a warning instead of
                # letting the error 500 the whole lookup.
                context = None
                if self.settings is not None and self.settings.use_real_apis:
                    return SequenceContextResult(
                        query=query,
                        warnings=[WORKBENCH_SEQUENCE_CONTEXT_RESOLVER_ERROR],
                    )
            if context is not None:
                return SequenceContextResult(query=query, context=context)
            if self.settings is not None and self.settings.use_real_apis:
                return SequenceContextResult(
                    query=query,
                    warnings=[WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE],
                )

        context = self.fixture_provider.resolve(query, normalized_species)
        if context is not None:
            return SequenceContextResult(query=query, context=context)
        return SequenceContextResult(
            query=query,
            warnings=[WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE],
        )
