from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.services.clinvar_local import (
    CLINVAR_SOURCE_ID,
    ClinVarLocalLookup,
    ClinVarLocalStore,
)
from app.services.dbsnp_local import (
    DBSNP_SOURCE_ID,
    DbSnpAlleleIdentity,
    DbSnpLocalLookup,
    DbSnpLocalRecord,
    DbSnpLocalStore,
)
from app.services.repeatmasker_local import (
    REPEATMASKER_SOURCE_ID,
    RepeatMaskerLocalQuery,
    RepeatMaskerLocalStore,
)
from app.services.sequence_window_model import (
    LocalSequenceWindowBuilder,
    LocalSequenceWindowContext,
)
from app.services.transcript_model import (
    GENCODE_SOURCE_ID,
    MANE_SOURCE_ID,
    TranscriptCoordinateLookup,
    TranscriptModelStore,
)

LOCAL_EVIDENCE_SOURCE_ORDER = (
    DBSNP_SOURCE_ID,
    CLINVAR_SOURCE_ID,
    MANE_SOURCE_ID,
    GENCODE_SOURCE_ID,
    REPEATMASKER_SOURCE_ID,
)

LOCAL_EVIDENCE_RUNTIME_FLOWS = ("lookup", "search", "gene_viewer", "workbench")


@dataclass(frozen=True)
class LocalEvidenceRuntimeDecision:
    flow: str
    enabled: bool
    reason: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalEvidenceRuntimeGate:
    enabled: bool = False
    allowed_flows: tuple[str, ...] = ()
    require_real_apis: bool = True
    use_real_apis: bool = False
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_settings(cls, settings: object) -> "LocalEvidenceRuntimeGate":
        allowed_flows, warnings = _configured_local_evidence_flows(
            getattr(settings, "local_evidence_allowed_flows_raw", "")
        )
        return cls(
            enabled=_as_bool(getattr(settings, "local_evidence_enabled", False)),
            allowed_flows=allowed_flows,
            require_real_apis=_as_bool(getattr(settings, "local_evidence_require_real_apis", True)),
            use_real_apis=_as_bool(getattr(settings, "use_real_apis", False)),
            warnings=warnings,
        )

    def for_flow(self, flow: str) -> LocalEvidenceRuntimeDecision:
        normalized_flow = _normalize_flow_name(flow)
        if normalized_flow not in LOCAL_EVIDENCE_RUNTIME_FLOWS:
            return LocalEvidenceRuntimeDecision(
                flow=normalized_flow,
                enabled=False,
                reason="local_evidence_unknown_flow",
                warnings=(*self.warnings, "local_evidence_unknown_flow"),
            )
        if not self.enabled:
            return LocalEvidenceRuntimeDecision(
                flow=normalized_flow,
                enabled=False,
                reason="local_evidence_disabled",
                warnings=self.warnings,
            )
        if self.require_real_apis and not self.use_real_apis:
            return LocalEvidenceRuntimeDecision(
                flow=normalized_flow,
                enabled=False,
                reason="local_evidence_real_apis_required",
                warnings=self.warnings,
            )
        if normalized_flow not in self.allowed_flows:
            return LocalEvidenceRuntimeDecision(
                flow=normalized_flow,
                enabled=False,
                reason="local_evidence_flow_not_enabled",
                warnings=self.warnings,
            )
        return LocalEvidenceRuntimeDecision(
            flow=normalized_flow,
            enabled=True,
            reason="local_evidence_enabled",
            warnings=self.warnings,
        )

    def allows(self, flow: str) -> bool:
        return self.for_flow(flow).enabled


@dataclass(frozen=True)
class LocalEvidenceVariantIdentity:
    chrom: str
    position: int
    ref: str
    alt: str
    variant_id: str
    source: str
    genomic_hgvs: str | None = None
    rsid: str | None = None


@dataclass(frozen=True)
class LocalEvidenceBundle:
    query_kind: str
    submitted_query: str
    variant_identity: LocalEvidenceVariantIdentity | None
    dbsnp: DbSnpLocalLookup | None = None
    clinvar: ClinVarLocalLookup | None = None
    transcript_coordinate: TranscriptCoordinateLookup | None = None
    repeatmasker: RepeatMaskerLocalQuery | None = None
    sequence_context: LocalSequenceWindowContext | None = None
    provenance: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    unavailable_reason: str | None = None

    @property
    def available(self) -> bool:
        return self.variant_identity is not None and self.unavailable_reason is None


class LocalEvidenceOrchestrator:
    """Backend-only composition layer for fixture-first local evidence models.

    This service intentionally returns internal dataclasses. It is not wired to
    public routes, Pydantic schemas, source cache, or frontend mirrors.
    """

    def __init__(
        self,
        *,
        dbsnp_store: DbSnpLocalStore | None = None,
        clinvar_store: ClinVarLocalStore | None = None,
        transcript_store: TranscriptModelStore | None = None,
        repeatmasker_store: RepeatMaskerLocalStore | None = None,
        sequence_builder: LocalSequenceWindowBuilder | None = None,
        coordinate_resolver: object | None = None,
    ) -> None:
        self.dbsnp_store = dbsnp_store or DbSnpLocalStore()
        self.clinvar_store = clinvar_store or ClinVarLocalStore()
        self.transcript_store = transcript_store or TranscriptModelStore()
        self.repeatmasker_store = repeatmasker_store or RepeatMaskerLocalStore()
        self.sequence_builder = sequence_builder or LocalSequenceWindowBuilder()
        self.coordinate_resolver = coordinate_resolver

    def resolve_cdna(
        self,
        *,
        gene: str,
        cdna_hgvs: str,
        transcript: str | None = None,
        include_sequence: bool = False,
        repeatmasker_flank_bp: int = 25,
        sequence_flank_bp: int | None = None,
    ) -> LocalEvidenceBundle:
        if self.coordinate_resolver is None:
            return LocalEvidenceBundle(
                query_kind="cdna",
                submitted_query=f"{gene}:{cdna_hgvs}",
                variant_identity=None,
                warnings=("local_evidence_coordinate_resolver_unavailable",),
                unavailable_reason="coordinate_resolver_unavailable",
            )
        try:
            resolved = self.coordinate_resolver.resolve(
                gene=gene,
                cdna=cdna_hgvs,
                transcript=transcript,
            )
        except Exception:
            resolved = None
        if resolved is None:
            return LocalEvidenceBundle(
                query_kind="cdna",
                submitted_query=f"{gene}:{cdna_hgvs}",
                variant_identity=None,
                warnings=("local_evidence_coordinate_resolution_unavailable",),
                unavailable_reason="coordinate_resolution_unavailable",
            )
        return self.resolve_variant(
            gene=gene,
            chrom=resolved.chrom,
            position=resolved.pos,
            ref=resolved.ref,
            alt=resolved.alt,
            transcript=transcript or resolved.transcript,
            cdna_hgvs=cdna_hgvs,
            include_sequence=include_sequence,
            repeatmasker_flank_bp=repeatmasker_flank_bp,
            sequence_flank_bp=sequence_flank_bp,
            submitted_query=f"{gene}:{cdna_hgvs}",
            query_kind="cdna",
        )

    def resolve_rsid(
        self,
        rsid: str,
        *,
        gene: str | None = None,
        transcript: str | None = None,
        requested_alt: str | None = None,
        cdna_hgvs: str | None = None,
        include_sequence: bool = False,
        repeatmasker_flank_bp: int = 25,
        sequence_flank_bp: int | None = None,
    ) -> LocalEvidenceBundle:
        normalized_requested_alt = None
        if requested_alt is not None:
            normalized_requested_alt = _normalize_local_allele(requested_alt)
            if normalized_requested_alt is None:
                return LocalEvidenceBundle(
                    query_kind="rsid",
                    submitted_query=rsid,
                    variant_identity=None,
                    warnings=("local_evidence_invalid_allele",),
                    unavailable_reason="invalid_allele",
                )

        dbsnp_lookup = self.dbsnp_store.lookup_rsid(rsid)
        if not dbsnp_lookup.available or dbsnp_lookup.record is None:
            return LocalEvidenceBundle(
                query_kind="rsid",
                submitted_query=rsid,
                variant_identity=None,
                dbsnp=dbsnp_lookup,
                provenance=_dbsnp_provenance(dbsnp_lookup),
                warnings=dbsnp_lookup.warnings,
                unavailable_reason=dbsnp_lookup.unavailable_reason,
            )

        allele_identity = _single_allele_identity(
            dbsnp_lookup.record,
            requested_alt=normalized_requested_alt,
        )
        if allele_identity is None:
            unavailable_reason = (
                "rsid_allele_mismatch"
                if normalized_requested_alt is not None
                else "ambiguous_rsid_alleles"
            )
            warning = (
                "local_evidence_rsid_allele_mismatch"
                if normalized_requested_alt is not None
                else "local_evidence_ambiguous_rsid_alleles"
            )
            return LocalEvidenceBundle(
                query_kind="rsid",
                submitted_query=rsid,
                variant_identity=None,
                dbsnp=dbsnp_lookup,
                provenance=_dbsnp_provenance(dbsnp_lookup),
                warnings=(warning,),
                unavailable_reason=unavailable_reason,
            )

        return self._resolve_identity(
            query_kind="rsid",
            submitted_query=rsid,
            identity=_variant_identity_from_dbsnp(dbsnp_lookup.record, allele_identity),
            dbsnp_lookup=dbsnp_lookup,
            gene=gene,
            transcript=transcript,
            cdna_hgvs=cdna_hgvs,
            include_sequence=include_sequence,
            repeatmasker_flank_bp=repeatmasker_flank_bp,
            sequence_flank_bp=sequence_flank_bp,
        )

    def resolve_variant_id(
        self,
        variant_id: str,
        *,
        gene: str | None = None,
        transcript: str | None = None,
        cdna_hgvs: str | None = None,
        include_sequence: bool = False,
        repeatmasker_flank_bp: int = 25,
        sequence_flank_bp: int | None = None,
    ) -> LocalEvidenceBundle:
        parsed = _parse_variant_id(variant_id)
        if parsed is None:
            return LocalEvidenceBundle(
                query_kind="variant_id",
                submitted_query=variant_id,
                variant_identity=None,
                warnings=("local_evidence_invalid_variant_id",),
                unavailable_reason="invalid_variant_id",
            )
        chrom, position, ref, alt = parsed
        return self.resolve_variant(
            gene=gene,
            chrom=chrom,
            position=position,
            ref=ref,
            alt=alt,
            transcript=transcript,
            cdna_hgvs=cdna_hgvs,
            include_sequence=include_sequence,
            repeatmasker_flank_bp=repeatmasker_flank_bp,
            sequence_flank_bp=sequence_flank_bp,
            submitted_query=variant_id,
            query_kind="variant_id",
        )

    def resolve_variant(
        self,
        *,
        gene: str | None,
        chrom: str,
        position: int,
        ref: str,
        alt: str,
        transcript: str | None = None,
        cdna_hgvs: str | None = None,
        include_sequence: bool = False,
        repeatmasker_flank_bp: int = 25,
        sequence_flank_bp: int | None = None,
        submitted_query: str | None = None,
        query_kind: str = "variant",
    ) -> LocalEvidenceBundle:
        if position < 1:
            return LocalEvidenceBundle(
                query_kind=query_kind,
                submitted_query=submitted_query or f"{chrom}-{position}-{ref}-{alt}",
                variant_identity=None,
                warnings=("local_evidence_invalid_coordinates",),
                unavailable_reason="invalid_coordinates",
            )
        normalized_ref = _normalize_local_allele(ref)
        normalized_alt = _normalize_local_allele(alt)
        if normalized_ref is None or normalized_alt is None:
            return LocalEvidenceBundle(
                query_kind=query_kind,
                submitted_query=submitted_query or f"{chrom}-{position}-{ref}-{alt}",
                variant_identity=None,
                warnings=("local_evidence_invalid_allele",),
                unavailable_reason="invalid_allele",
            )

        dbsnp_lookup = self.dbsnp_store.lookup_variant(
            chrom=chrom,
            position=position,
            ref=normalized_ref,
            alt=normalized_alt,
        )
        identity = LocalEvidenceVariantIdentity(
            chrom=_normalize_chrom(chrom),
            position=position,
            ref=normalized_ref,
            alt=normalized_alt,
            variant_id=_variant_id(chrom, position, normalized_ref, normalized_alt),
            genomic_hgvs=_refseq_genomic_hgvs(chrom, position, normalized_ref, normalized_alt),
            rsid=(
                dbsnp_lookup.record.rsid if dbsnp_lookup.available and dbsnp_lookup.record else None
            ),
            source="submitted_variant",
        )
        return self._resolve_identity(
            query_kind=query_kind,
            submitted_query=submitted_query or identity.variant_id,
            identity=identity,
            dbsnp_lookup=dbsnp_lookup,
            gene=gene,
            transcript=transcript,
            cdna_hgvs=cdna_hgvs,
            include_sequence=include_sequence,
            repeatmasker_flank_bp=repeatmasker_flank_bp,
            sequence_flank_bp=sequence_flank_bp,
        )

    def _resolve_identity(
        self,
        *,
        query_kind: str,
        submitted_query: str,
        identity: LocalEvidenceVariantIdentity,
        dbsnp_lookup: DbSnpLocalLookup | None,
        gene: str | None,
        transcript: str | None,
        cdna_hgvs: str | None,
        include_sequence: bool,
        repeatmasker_flank_bp: int,
        sequence_flank_bp: int | None,
    ) -> LocalEvidenceBundle:
        warnings: list[str] = []
        if dbsnp_lookup is not None:
            warnings.extend(dbsnp_lookup.warnings)

        clinvar_lookup = self.clinvar_store.lookup(
            chrom=identity.chrom,
            position=identity.position,
            ref=identity.ref,
            alt=identity.alt,
        )
        warnings.extend(clinvar_lookup.warnings)

        active_gene = _normalize_gene(gene) or _gene_from_clinvar(clinvar_lookup)
        transcript_coordinate: TranscriptCoordinateLookup | None = None
        if active_gene is None:
            warnings.append("local_evidence_gene_required_for_transcript_model")
        else:
            transcript_coordinate = self.transcript_store.map_coordinate(
                gene=active_gene,
                chrom=identity.chrom,
                position=identity.position,
                transcript=transcript,
            )
            warnings.extend(transcript_coordinate.warnings)

        repeatmasker = self.repeatmasker_store.query_window(
            chrom=identity.chrom,
            start=max(1, identity.position - repeatmasker_flank_bp),
            end=identity.position + len(identity.ref) - 1 + repeatmasker_flank_bp,
        )
        warnings.extend(repeatmasker.warnings)

        sequence_context: LocalSequenceWindowContext | None = None
        if include_sequence:
            sequence_context = self.sequence_builder.build(
                chrom=identity.chrom,
                position=identity.position,
                reference_allele=identity.ref,
                alternate_allele=identity.alt,
                gene=active_gene,
                transcript=_sequence_transcript(transcript_coordinate, transcript),
                cdna_hgvs=cdna_hgvs or _cdna_hgvs_from_clinvar(clinvar_lookup),
                genomic_hg38=identity.variant_id,
                strand=_coordinate_strand(transcript_coordinate),
                flank_bp=sequence_flank_bp,
            )
            warnings.extend(sequence_context.warnings)

        return LocalEvidenceBundle(
            query_kind=query_kind,
            submitted_query=submitted_query,
            variant_identity=identity,
            dbsnp=dbsnp_lookup,
            clinvar=clinvar_lookup,
            transcript_coordinate=transcript_coordinate,
            repeatmasker=repeatmasker,
            sequence_context=sequence_context,
            provenance=_provenance_tokens(
                identity=identity,
                dbsnp_lookup=dbsnp_lookup,
                clinvar_lookup=clinvar_lookup,
                transcript_coordinate=transcript_coordinate,
                repeatmasker=repeatmasker,
                sequence_context=sequence_context,
            ),
            warnings=_dedupe(warnings),
        )


def _single_allele_identity(
    record: DbSnpLocalRecord,
    *,
    requested_alt: str | None,
) -> DbSnpAlleleIdentity | None:
    if requested_alt is not None:
        for identity in record.allele_identities:
            if identity.alt == requested_alt:
                return identity
        return None
    if len(record.allele_identities) != 1:
        return None
    return record.allele_identities[0]


def _variant_identity_from_dbsnp(
    record: DbSnpLocalRecord,
    identity: DbSnpAlleleIdentity,
) -> LocalEvidenceVariantIdentity:
    return LocalEvidenceVariantIdentity(
        chrom=identity.chrom,
        position=identity.position,
        ref=identity.ref,
        alt=identity.alt,
        variant_id=identity.gnomad_variant_id,
        genomic_hgvs=identity.genomic_hgvs,
        rsid=record.rsid,
        source=DBSNP_SOURCE_ID,
    )


def _dbsnp_provenance(lookup: DbSnpLocalLookup | None) -> tuple[str, ...]:
    if lookup is None:
        return ()
    if lookup.record is None:
        return (f"{DBSNP_SOURCE_ID}:no_record",)
    return (f"{DBSNP_SOURCE_ID}:{lookup.record.rsid}",)


def _provenance_tokens(
    *,
    identity: LocalEvidenceVariantIdentity,
    dbsnp_lookup: DbSnpLocalLookup | None,
    clinvar_lookup: ClinVarLocalLookup,
    transcript_coordinate: TranscriptCoordinateLookup | None,
    repeatmasker: RepeatMaskerLocalQuery,
    sequence_context: LocalSequenceWindowContext | None,
) -> tuple[str, ...]:
    tokens = [f"variant_identity:{identity.source}:{identity.variant_id}"]
    tokens.extend(_dbsnp_provenance(dbsnp_lookup))

    if clinvar_lookup.record is not None:
        tokens.append(f"{CLINVAR_SOURCE_ID}:{clinvar_lookup.record.record_id}")
    else:
        tokens.append(f"{CLINVAR_SOURCE_ID}:no_record")

    if transcript_coordinate is not None and transcript_coordinate.location is not None:
        tokens.append(
            "transcript_model:"
            f"{transcript_coordinate.location.transcript}:"
            f"{transcript_coordinate.location.region}"
        )
    elif transcript_coordinate is not None:
        tokens.append(f"transcript_model:{transcript_coordinate.unavailable_reason}")

    if repeatmasker.available:
        tokens.append(f"{REPEATMASKER_SOURCE_ID}:hits={len(repeatmasker.repeats)}")
    else:
        tokens.append(f"{REPEATMASKER_SOURCE_ID}:{repeatmasker.unavailable_reason}")

    if sequence_context is not None and sequence_context.provenance is not None:
        status = sequence_context.unavailable_reason or "available"
        tokens.append(f"{sequence_context.provenance.source_id}:{status}")
    return tuple(tokens)


def _gene_from_clinvar(lookup: ClinVarLocalLookup) -> str | None:
    if lookup.record is None or not lookup.record.gene_symbols:
        return None
    return lookup.record.gene_symbols[0]


def _cdna_hgvs_from_clinvar(lookup: ClinVarLocalLookup) -> str | None:
    if lookup.record is None:
        return None
    for alias in lookup.record.hgvs_aliases:
        if ":c." in alias:
            return alias
    return None


def _sequence_transcript(
    transcript_coordinate: TranscriptCoordinateLookup | None,
    transcript: str | None,
) -> str | None:
    if transcript_coordinate is not None and transcript_coordinate.location is not None:
        return transcript_coordinate.location.transcript
    return transcript


def _coordinate_strand(transcript_coordinate: TranscriptCoordinateLookup | None) -> str:
    if transcript_coordinate is not None and transcript_coordinate.location is not None:
        return transcript_coordinate.location.strand
    return "unknown"


def _parse_variant_id(value: str) -> tuple[str, int, str, str] | None:
    match = re.fullmatch(r"([^-]+)-(\d+)-([A-Za-z]+)-([A-Za-z]+)", value.strip())
    if match is None:
        return None
    chrom, position, ref, alt = match.groups()
    normalized_ref = _normalize_local_allele(ref)
    normalized_alt = _normalize_local_allele(alt)
    if normalized_ref is None or normalized_alt is None:
        return None
    return chrom, int(position), normalized_ref, normalized_alt


def _variant_id(chrom: str, position: int, ref: str, alt: str) -> str:
    return f"{_normalize_chrom(chrom)}-{position}-{ref.strip().upper()}-{alt.strip().upper()}"


def _refseq_genomic_hgvs(chrom: str, position: int, ref: str, alt: str) -> str | None:
    normalized_chrom = _normalize_chrom(chrom)
    if not (
        len(ref.strip()) == 1
        and len(alt.strip()) == 1
        and ref.strip().upper() in {"A", "C", "G", "T"}
        and alt.strip().upper() in {"A", "C", "G", "T"}
    ):
        return None
    try:
        chrom_number = int(normalized_chrom)
    except ValueError:
        return None
    if not 1 <= chrom_number <= 22:
        return None
    return f"NC_{chrom_number:06d}.11:g.{position}{ref.strip().upper()}>{alt.strip().upper()}"


def _normalize_local_allele(value: str) -> str | None:
    normalized = value.strip().upper()
    if not normalized or any(base not in {"A", "C", "G", "T", "N"} for base in normalized):
        return None
    return normalized


def _normalize_chrom(chrom: str) -> str:
    normalized = chrom.strip()
    if normalized.lower().startswith("chr"):
        normalized = normalized[3:]
    normalized = normalized.upper()
    match = re.fullmatch(r"NC_0*(\d+)\.\d+", normalized)
    if match is not None:
        number = int(match.group(1))
        if 1 <= number <= 22:
            return str(number)
        if number == 23:
            return "X"
        if number == 24:
            return "Y"
    if normalized == "MT":
        return "M"
    return normalized


def _normalize_gene(gene: str | None) -> str | None:
    if gene is None:
        return None
    normalized = gene.strip().upper()
    return normalized or None


def _configured_local_evidence_flows(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if value is None:
        return (), ()

    allowed: list[str] = []
    warnings: list[str] = []
    for raw_token in str(value).split(","):
        token = _normalize_flow_name(raw_token)
        if not token:
            continue
        if token == "all":
            allowed.extend(LOCAL_EVIDENCE_RUNTIME_FLOWS)
            continue
        if token not in LOCAL_EVIDENCE_RUNTIME_FLOWS:
            warnings.append(f"local_evidence_unknown_configured_flow:{token}")
            continue
        allowed.append(token)
    return _dedupe(allowed), _dedupe(warnings)


def _normalize_flow_name(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
