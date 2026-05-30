from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import gzip
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.data_sources import DEFAULT_DATA_SOURCE_REGISTRY, DataSourceRegistry
from app.data_sources.protein_assets import PROTEIN_ANNOTATION_ASSETS, ProteinAssetSpec
from app.repos.protein_annotation_cache_repo import ProteinAnnotationCacheRepo
from app.schemas.gene_viewer import ProteinDomain, ProteinFeatures
from app.schemas.protein_annotation import (
    ProteinAnnotationRequest,
    ProteinDomainTrack,
    ProteinDomainTrackFeature,
    ProteinTrackProvenance,
)

PROTEIN_ANNOTATION_SOURCE = "eamos_protein_annotation_super_tool"
_PROTEIN_ALPHABET_RE = re.compile(r"^[ABCDEFGHIKLMNPQRSTVWXYZUO*]+$")
_DNA_RE = re.compile(r"^[ACGTUNacgtun]+$")
HMMPRESS_SUFFIXES = (".h3f", ".h3i", ".h3m", ".h3p")
_UNIPROT_FEATURE_KIND_MAP = {
    "DOMAIN": "domain",
    "REGION": "region",
    "MOTIF": "motif",
    "REPEAT": "repeat",
    "SITE": "site",
    "ACT_SITE": "site",
    "BINDING": "site",
    "MOD_RES": "site",
    "CARBOHYD": "site",
    "LIPID": "site",
    "DISULFID": "site",
    "NON_STD": "site",
    "COILED": "coiled_coil",
    "COMPBIAS": "low_complexity",
    "SIGNAL": "signal_peptide",
    "TRANSMEM": "transmembrane",
    "TOPO_DOM": "topological_domain",
}

_CODON_TABLE = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TTG": "L",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "TAT": "Y",
    "TAC": "Y",
    "TAA": "*",
    "TAG": "*",
    "TGT": "C",
    "TGC": "C",
    "TGA": "*",
    "TGG": "W",
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CTG": "L",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "ATT": "I",
    "ATC": "I",
    "ATA": "I",
    "ATG": "M",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GTG": "V",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}


@dataclass(frozen=True)
class NormalizedProteinInput:
    submitted_sequence: str
    protein_sequence: str
    translated_from: str
    sequence_hash: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class HmmerRuntimeStatus:
    ready: bool
    reason: str | None = None
    hmmscan_path: str | None = None
    pfam_hmm_path: str | None = None
    missing_indexes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProteinFeatureProviderResult:
    features: tuple[ProteinDomainTrackFeature, ...] = ()
    warnings: tuple[str, ...] = ()


class HmmerRunner(Protocol):
    def status(self) -> HmmerRuntimeStatus: ...

    def run(self, *, protein_sequence: str, sequence_hash: str) -> str: ...


class ProteinFeatureProvider(Protocol):
    def features_for_request(
        self,
        request: ProteinAnnotationRequest,
        *,
        protein_length: int,
    ) -> ProteinFeatureProviderResult: ...


class LocalHmmerRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> HmmerRuntimeStatus:
        hmmscan = resolve_executable(self.settings.protein_annotation_hmmscan_path)
        pfam_hmm = resolve_protein_runtime_path(
            self.settings,
            self.settings.protein_annotation_pfam_hmm_path,
        )
        missing_indexes = tuple(
            str(pfam_hmm.with_suffix(pfam_hmm.suffix + suffix))
            for suffix in HMMPRESS_SUFFIXES
            if not pfam_hmm.with_suffix(pfam_hmm.suffix + suffix).is_file()
        )
        if hmmscan is None:
            return HmmerRuntimeStatus(
                ready=False,
                reason="hmmscan_executable_missing",
                pfam_hmm_path=str(pfam_hmm),
            )
        if not pfam_hmm.is_file():
            return HmmerRuntimeStatus(
                ready=False,
                reason="pfam_hmm_database_missing",
                hmmscan_path=hmmscan,
                pfam_hmm_path=str(pfam_hmm),
            )
        if pfam_hmm.suffix.lower() == ".gz":
            return HmmerRuntimeStatus(
                ready=False,
                reason="pfam_hmm_database_not_extracted_or_pressed",
                hmmscan_path=hmmscan,
                pfam_hmm_path=str(pfam_hmm),
                warnings=("staged_pfam_hmm_gz_is_not_a_runtime_index",),
            )
        if self.settings.protein_annotation_require_pfam_indexes and missing_indexes:
            return HmmerRuntimeStatus(
                ready=False,
                reason="pfam_hmmpress_indexes_missing",
                hmmscan_path=hmmscan,
                pfam_hmm_path=str(pfam_hmm),
                missing_indexes=missing_indexes,
            )
        return HmmerRuntimeStatus(
            ready=True,
            hmmscan_path=hmmscan,
            pfam_hmm_path=str(pfam_hmm),
        )

    def run(self, *, protein_sequence: str, sequence_hash: str) -> str:
        runtime = self.status()
        if not runtime.ready or runtime.hmmscan_path is None or runtime.pfam_hmm_path is None:
            raise RuntimeError(runtime.reason or "hmmscan_runtime_unavailable")
        with tempfile.TemporaryDirectory(prefix="eamos-protein-") as temp_dir:
            temp_path = Path(temp_dir)
            fasta_path = temp_path / "query.faa"
            domtblout_path = temp_path / "hmmscan.domtblout"
            fasta_path.write_text(f">eamos_{sequence_hash[:16]}\n{protein_sequence}\n")
            result = subprocess.run(
                [
                    runtime.hmmscan_path,
                    "--noali",
                    "--domtblout",
                    str(domtblout_path),
                    runtime.pfam_hmm_path,
                    str(fasta_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.settings.protein_annotation_hmmscan_timeout_seconds,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"hmmscan_failed:{stderr[:200]}")
            return domtblout_path.read_text(encoding="utf-8")


class UniProtFlatfileFeatureProvider:
    def __init__(
        self,
        settings: Settings,
        *,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        self.settings = settings
        self.registry = registry

    def features_for_request(
        self,
        request: ProteinAnnotationRequest,
        *,
        protein_length: int,
    ) -> ProteinFeatureProviderResult:
        if not request.gene_symbol and not request.protein_accession:
            return ProteinFeatureProviderResult()

        path = resolve_protein_runtime_path(
            self.settings,
            self.settings.protein_annotation_uniprot_dat_path,
        )
        if not path.is_file():
            return ProteinFeatureProviderResult(
                warnings=("uniprot_flatfile_missing_no_live_api_fallback",)
            )

        started_at = time.monotonic()
        try:
            entry = _find_uniprot_entry(
                path=path,
                gene_symbol=request.gene_symbol,
                protein_accession=request.protein_accession,
                timeout_seconds=self.settings.protein_annotation_uniprot_scan_timeout_seconds,
                started_at=started_at,
            )
        except TimeoutError:
            return ProteinFeatureProviderResult(
                warnings=("uniprot_flatfile_scan_timeout_no_live_api_fallback",)
            )
        if entry is None:
            return ProteinFeatureProviderResult(warnings=("uniprot_entry_not_found",))

        source_release = self.registry.get("uniprotkb_reviewed_swissprot").source_version
        features = parse_uniprot_flatfile_features(
            entry,
            protein_length=protein_length,
            source_release=source_release,
            source_checksum_sha256=_asset_sha256("uniprot_sprot_dat_gz"),
        )
        return ProteinFeatureProviderResult(features=tuple(features))


class ProteinAnnotationService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        cache_repo: ProteinAnnotationCacheRepo | None = None,
        runner: HmmerRunner | None = None,
        feature_provider: ProteinFeatureProvider | None = None,
        registry: DataSourceRegistry = DEFAULT_DATA_SOURCE_REGISTRY,
    ) -> None:
        self.settings = settings
        self.cache_repo = cache_repo
        self.registry = registry
        self.runner = runner or (LocalHmmerRunner(settings) if settings is not None else None)
        self.feature_provider = feature_provider or (
            UniProtFlatfileFeatureProvider(settings, registry=registry)
            if settings is not None and settings.protein_annotation_uniprot_features_enabled
            else None
        )

    def annotate(self, request: ProteinAnnotationRequest) -> ProteinDomainTrack:
        try:
            normalized = normalize_protein_input(request.sequence, input_type=request.input_type)
        except ValueError as exc:
            return _unavailable_track(
                f"sequence_normalization_failed:{exc}",
                sequence_label=request.sequence_label,
                gene_symbol=request.gene_symbol,
                transcript=request.transcript,
                protein_accession=request.protein_accession,
            )

        pfam_release = self.registry.get("interpro_pfam_protein_matches").source_version
        hmmer_release = self.registry.get("hmmer_pfam_a").source_version
        uniprot_release = self.registry.get("uniprotkb_reviewed_swissprot").source_version
        if not pfam_release or not hmmer_release:
            return _unavailable_track(
                "protein_annotation_provenance_missing",
                protein_length=len(normalized.protein_sequence),
                sequence_hash=normalized.sequence_hash,
                sequence_label=request.sequence_label,
                gene_symbol=request.gene_symbol,
                transcript=request.transcript,
                protein_accession=request.protein_accession,
                translated_from=normalized.translated_from,
                warnings=[*normalized.warnings],
            )

        cache_key = _cache_key(
            sequence_hash=normalized.sequence_hash,
            pfam_release=pfam_release,
            hmmer_release=hmmer_release,
            uniprot_release=uniprot_release,
        )
        if request.use_cache and self.cache_repo is not None:
            cached = self.cache_repo.get(
                sequence_hash=normalized.sequence_hash,
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
            )
            if cached is not None:
                return cached.model_copy(
                    update={
                        "status": "cache_hit",
                        "cache_status": "cache_hit",
                        "sequence_label": request.sequence_label,
                        "gene_symbol": request.gene_symbol,
                        "transcript": request.transcript,
                        "protein_accession": request.protein_accession,
                        "warnings": _dedupe(
                            [*cached.warnings, *normalized.warnings, "protein_annotation_cache_hit"]
                        ),
                    }
                )

        if not request.allow_run:
            return _unavailable_track(
                "protein_annotation_cache_miss",
                protein_length=len(normalized.protein_sequence),
                sequence_hash=normalized.sequence_hash,
                sequence_label=request.sequence_label,
                gene_symbol=request.gene_symbol,
                transcript=request.transcript,
                protein_accession=request.protein_accession,
                translated_from=normalized.translated_from,
                cache_key=cache_key,
                cache_status="cache_miss",
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
                warnings=[*normalized.warnings, "protein_annotation_cache_miss_no_runtime_run"],
            )
        if self.settings is None or not self.settings.protein_annotation_enabled:
            return _unavailable_track(
                "protein_annotation_disabled",
                protein_length=len(normalized.protein_sequence),
                sequence_hash=normalized.sequence_hash,
                sequence_label=request.sequence_label,
                gene_symbol=request.gene_symbol,
                transcript=request.transcript,
                protein_accession=request.protein_accession,
                translated_from=normalized.translated_from,
                cache_key=cache_key,
                cache_status="cache_miss",
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
                warnings=[*normalized.warnings, "no_live_protein_api_fallback"],
            )
        if self.runner is None:
            return _unavailable_track(
                "protein_annotation_runner_unconfigured",
                protein_length=len(normalized.protein_sequence),
                sequence_hash=normalized.sequence_hash,
                sequence_label=request.sequence_label,
                gene_symbol=request.gene_symbol,
                transcript=request.transcript,
                protein_accession=request.protein_accession,
                translated_from=normalized.translated_from,
                cache_key=cache_key,
                cache_status="cache_miss",
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
                warnings=[*normalized.warnings, "no_live_protein_api_fallback"],
            )

        runtime = self.runner.status()
        if not runtime.ready:
            return _unavailable_track(
                runtime.reason or "protein_annotation_runtime_unavailable",
                protein_length=len(normalized.protein_sequence),
                sequence_hash=normalized.sequence_hash,
                sequence_label=request.sequence_label,
                gene_symbol=request.gene_symbol,
                transcript=request.transcript,
                protein_accession=request.protein_accession,
                translated_from=normalized.translated_from,
                cache_key=cache_key,
                cache_status="cache_miss",
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
                warnings=[*normalized.warnings, *runtime.warnings, "no_live_protein_api_fallback"],
            )

        try:
            domtblout = self.runner.run(
                protein_sequence=normalized.protein_sequence,
                sequence_hash=normalized.sequence_hash,
            )
        except Exception as exc:
            return _unavailable_track(
                f"hmmscan_failed:{type(exc).__name__}",
                protein_length=len(normalized.protein_sequence),
                sequence_hash=normalized.sequence_hash,
                sequence_label=request.sequence_label,
                gene_symbol=request.gene_symbol,
                transcript=request.transcript,
                protein_accession=request.protein_accession,
                translated_from=normalized.translated_from,
                cache_key=cache_key,
                cache_status="cache_miss",
                pfam_release=pfam_release,
                hmmer_release=hmmer_release,
                uniprot_release=uniprot_release,
                warnings=[*normalized.warnings, "no_live_protein_api_fallback"],
            )

        hmmer_features = parse_hmmer_domtblout(
            domtblout,
            pfam_release=pfam_release,
            pfam_checksum_sha256=_asset_sha256("pfam_a_hmm_gz"),
        )
        provider_result = (
            self.feature_provider.features_for_request(
                request,
                protein_length=len(normalized.protein_sequence),
            )
            if self.feature_provider is not None
            else ProteinFeatureProviderResult()
        )
        features = sorted(
            _dedupe_features([*provider_result.features, *hmmer_features]),
            key=lambda item: (item.aa_start, item.aa_end, item.source, item.label),
        )
        warnings = [*normalized.warnings]
        warnings.extend(provider_result.warnings)
        if (
            self.feature_provider is None
            and (request.gene_symbol or request.protein_accession)
            and not hmmer_features
        ):
            warnings.append("protein_named_feature_provider_not_configured")
        if not features:
            warnings.append("protein_annotation_no_pfam_hits")
        track = ProteinDomainTrack(
            status="available",
            sequence_label=request.sequence_label,
            gene_symbol=request.gene_symbol,
            transcript=request.transcript,
            protein_accession=request.protein_accession,
            protein_sequence_hash=normalized.sequence_hash,
            protein_length=len(normalized.protein_sequence),
            translated_from=normalized.translated_from,
            cache_key=cache_key,
            cache_status="stored" if self.cache_repo is not None else "not_used",
            pfam_release=pfam_release,
            hmmer_release=hmmer_release,
            uniprot_release=uniprot_release,
            features=features,
            provenance=_protein_track_provenance(self.registry),
            warnings=_dedupe(warnings),
        )
        if request.use_cache and self.cache_repo is not None:
            self.cache_repo.upsert(track)
        return track


def normalize_protein_input(sequence: str, *, input_type: str = "auto") -> NormalizedProteinInput:
    cleaned = _clean_sequence(sequence)
    if not cleaned:
        raise ValueError("empty_sequence")
    detected_type = input_type
    if detected_type == "auto":
        detected_type = "coding_dna" if _DNA_RE.fullmatch(cleaned) else "protein"
    if detected_type == "coding_dna":
        protein, warnings = _translate_coding_dna(cleaned)
        return NormalizedProteinInput(
            submitted_sequence=cleaned,
            protein_sequence=protein,
            translated_from="coding_dna",
            sequence_hash=_sha256_text(protein),
            warnings=tuple(warnings),
        )
    if detected_type != "protein":
        raise ValueError("unsupported_input_type")
    if not _PROTEIN_ALPHABET_RE.fullmatch(cleaned):
        raise ValueError("invalid_protein_characters")
    protein = cleaned.replace("*", "")
    if not protein:
        raise ValueError("empty_protein_sequence")
    return NormalizedProteinInput(
        submitted_sequence=cleaned,
        protein_sequence=protein,
        translated_from="protein",
        sequence_hash=_sha256_text(protein),
    )


def parse_hmmer_domtblout(
    text: str,
    *,
    pfam_release: str | None,
    pfam_checksum_sha256: str | None,
) -> list[ProteinDomainTrackFeature]:
    features: list[ProteinDomainTrackFeature] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=22)
        if len(parts) < 22:
            continue
        target_name = parts[0]
        accession = None if parts[1] == "-" else parts[1]
        try:
            independent_evalue = float(parts[12])
            domain_score = float(parts[13])
            hmm_start = int(parts[15])
            hmm_end = int(parts[16])
            aa_start = int(parts[17])
            aa_end = int(parts[18])
            envelope_start = int(parts[19])
            envelope_end = int(parts[20])
        except ValueError:
            continue
        label = parts[22].strip() if len(parts) >= 23 else ""
        if not label:
            label = target_name.replace("_", " ")
        aa_start, aa_end = sorted((aa_start, aa_end))
        feature_id = f"pfam:{accession or target_name}:{aa_start}-{aa_end}"
        features.append(
            ProteinDomainTrackFeature(
                feature_id=feature_id,
                kind="domain",
                label=label,
                short_label=_short_uniprot_feature_label(label),
                aa_start=aa_start,
                aa_end=aa_end,
                accession=accession,
                source="Pfam/HMMER hmmscan",
                source_accession=accession or target_name,
                source_release=pfam_release,
                source_checksum_sha256=pfam_checksum_sha256,
                score=domain_score,
                e_value=independent_evalue,
                hmm_start=min(hmm_start, hmm_end),
                hmm_end=max(hmm_start, hmm_end),
                envelope_start=min(envelope_start, envelope_end),
                envelope_end=max(envelope_start, envelope_end),
                description=_uniprot_feature_description(label),
                lane="domains",
            )
        )
    return sorted(
        _dedupe_features(features),
        key=lambda item: (item.aa_start, item.aa_end, item.accession or item.label),
    )


def parse_uniprot_flatfile_features(
    entry_text: str,
    *,
    protein_length: int,
    source_release: str | None,
    source_checksum_sha256: str | None,
) -> list[ProteinDomainTrackFeature]:
    accession = _primary_uniprot_accession(entry_text)
    features: list[ProteinDomainTrackFeature] = []
    current: dict[str, object] | None = None
    for raw_line in entry_text.splitlines():
        if not raw_line.startswith("FT"):
            continue
        payload = raw_line[5:].rstrip() if len(raw_line) > 5 else ""
        if not payload.strip():
            continue
        if payload[0].isspace():
            if current is not None:
                _apply_uniprot_feature_qualifier(current, payload.strip())
            continue

        if current is not None:
            feature = _uniprot_feature_from_current(
                current,
                accession=accession,
                protein_length=protein_length,
                source_release=source_release,
                source_checksum_sha256=source_checksum_sha256,
                ordinal=len(features) + 1,
            )
            if feature is not None:
                features.append(feature)
        parts = payload.split(None, 1)
        current = {"feature_key": parts[0], "location": parts[1] if len(parts) > 1 else ""}

    if current is not None:
        feature = _uniprot_feature_from_current(
            current,
            accession=accession,
            protein_length=protein_length,
            source_release=source_release,
            source_checksum_sha256=source_checksum_sha256,
            ordinal=len(features) + 1,
        )
        if feature is not None:
            features.append(feature)
    return sorted(
        _dedupe_features(features),
        key=lambda item: (item.aa_start, item.aa_end, item.source, item.label),
    )


def protein_features_from_domain_track(
    existing: ProteinFeatures,
    track: ProteinDomainTrack,
) -> ProteinFeatures:
    updated = existing.model_copy(deep=True)
    updated.domain_track = track
    if track.status not in {"available", "cache_hit"}:
        return updated
    existing_keys = {(item.aa_start, item.aa_end, item.label) for item in updated.domains}
    for feature in track.features:
        if feature.kind not in {
            "domain",
            "family",
            "motif",
            "repeat",
            "region",
            "coiled_coil",
            "low_complexity",
        }:
            continue
        label = feature.label
        key = (feature.aa_start, feature.aa_end, label)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        updated.domains.append(
            ProteinDomain(
                aa_start=feature.aa_start,
                aa_end=feature.aa_end,
                label=label,
                short_label=feature.short_label or label,
            )
        )
    updated.domains.sort(key=lambda item: (item.aa_start, item.aa_end, item.label))
    return updated


def _clean_sequence(sequence: str) -> str:
    lines = [line.strip() for line in sequence.splitlines() if not line.startswith(">")]
    return re.sub(r"[^A-Za-z*]", "", "".join(lines)).upper()


def _translate_coding_dna(sequence: str) -> tuple[str, list[str]]:
    if not _DNA_RE.fullmatch(sequence):
        raise ValueError("invalid_coding_dna_characters")
    normalized = sequence.upper().replace("U", "T")
    if len(normalized) % 3 != 0:
        raise ValueError("coding_dna_length_not_multiple_of_three")
    amino_acids: list[str] = []
    warnings: list[str] = []
    for index in range(0, len(normalized), 3):
        codon = normalized[index : index + 3]
        aa = "X" if "N" in codon else _CODON_TABLE.get(codon)
        if aa is None:
            raise ValueError(f"unknown_codon:{codon}")
        amino_acids.append(aa)
    if amino_acids and amino_acids[-1] == "*":
        amino_acids.pop()
        warnings.append("terminal_stop_codon_removed")
    if "*" in amino_acids:
        raise ValueError("internal_stop_codon")
    protein = "".join(amino_acids)
    if not protein:
        raise ValueError("empty_translation")
    return protein, warnings


def _find_uniprot_entry(
    *,
    path: Path,
    gene_symbol: str | None,
    protein_accession: str | None,
    timeout_seconds: float,
    started_at: float,
) -> str | None:
    requested_gene = (gene_symbol or "").upper()
    requested_accession = (protein_accession or "").upper()
    entry_lines: list[str] = []
    with _open_uniprot_text(path) as handle:
        for line in handle:
            if time.monotonic() - started_at > timeout_seconds:
                raise TimeoutError("uniprot_flatfile_scan_timeout")
            entry_lines.append(line)
            if not line.startswith("//"):
                continue
            entry = "".join(entry_lines)
            if _uniprot_entry_matches(
                entry,
                gene_symbol=requested_gene,
                protein_accession=requested_accession,
            ):
                return entry
            entry_lines = []
    return None


def _open_uniprot_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def _uniprot_entry_matches(
    entry: str,
    *,
    gene_symbol: str,
    protein_accession: str,
) -> bool:
    accessions = {accession.upper() for accession in _uniprot_accessions(entry)}
    genes = {gene.upper() for gene in _uniprot_gene_symbols(entry)}
    if protein_accession and protein_accession in accessions:
        return True
    return bool(gene_symbol and gene_symbol in genes)


def _uniprot_accessions(entry: str) -> list[str]:
    accessions: list[str] = []
    for line in entry.splitlines():
        if not line.startswith("AC"):
            continue
        values = line[5:].replace(";", " ").split()
        accessions.extend(value.strip() for value in values if value.strip())
    return accessions


def _primary_uniprot_accession(entry: str) -> str | None:
    accessions = _uniprot_accessions(entry)
    return accessions[0] if accessions else None


def _uniprot_gene_symbols(entry: str) -> list[str]:
    genes: list[str] = []
    for line in entry.splitlines():
        if not line.startswith("GN"):
            continue
        payload = line[5:]
        for key in ("Name", "Synonyms", "OrderedLocusNames", "ORFNames"):
            for match in re.finditer(rf"{key}=([^;]+)", payload):
                genes.extend(
                    item.strip() for item in re.split(r"[, ]+", match.group(1)) if item.strip()
                )
    return genes


def _apply_uniprot_feature_qualifier(current: dict[str, object], qualifier: str) -> None:
    if not qualifier.startswith("/"):
        return
    key, _, raw_value = qualifier[1:].partition("=")
    value = raw_value.strip().strip('"')
    if key in {"note", "id", "ligand", "ligand_id"} and value:
        current[str(key)] = value


def _uniprot_feature_from_current(
    current: dict[str, object],
    *,
    accession: str | None,
    protein_length: int,
    source_release: str | None,
    source_checksum_sha256: str | None,
    ordinal: int,
) -> ProteinDomainTrackFeature | None:
    feature_key = str(current.get("feature_key") or "")
    kind = _UNIPROT_FEATURE_KIND_MAP.get(feature_key)
    if kind is None:
        return None
    aa_range = _uniprot_location_range(str(current.get("location") or ""))
    if aa_range is None:
        return None
    aa_start, aa_end = aa_range
    if aa_start > protein_length or aa_end < 1:
        return None
    aa_start = max(1, aa_start)
    aa_end = min(protein_length, aa_end)
    label = _uniprot_feature_label(feature_key, current)
    if not label:
        return None
    source_accession = accession or "UniProtKB"
    return ProteinDomainTrackFeature(
        feature_id=f"uniprot:{source_accession}:{feature_key}:{aa_start}-{aa_end}:{ordinal}",
        kind=kind,
        label=label,
        short_label=_short_uniprot_feature_label(label),
        aa_start=aa_start,
        aa_end=aa_end,
        accession=accession,
        source="UniProtKB/Swiss-Prot feature table",
        source_accession=source_accession,
        source_release=source_release,
        source_checksum_sha256=source_checksum_sha256,
        description=_uniprot_feature_description(label),
        lane=_uniprot_feature_lane(kind),
    )


def _uniprot_location_range(location: str) -> tuple[int, int] | None:
    digits = [int(value) for value in re.findall(r"\d+", location)]
    if not digits:
        return None
    return min(digits), max(digits)


def _uniprot_feature_label(feature_key: str, current: dict[str, object]) -> str:
    for key in ("note", "id", "ligand"):
        value = str(current.get(key) or "").strip()
        if value:
            return value
    default_labels = {
        "SIGNAL": "Signal peptide",
        "TRANSMEM": "Transmembrane helix",
        "TOPO_DOM": "Topological domain",
        "COMPBIAS": "Compositional bias",
    }
    if feature_key in default_labels:
        return default_labels[feature_key]
    return feature_key.replace("_", " ").title()


def _short_uniprot_feature_label(label: str) -> str:
    normalized = label.lower()
    if normalized == "fz":
        return "CRD"
    transmembrane_match = re.search(r"transmembrane helix\s*(\d+)", normalized)
    if transmembrane_match:
        return f"TM{transmembrane_match.group(1)}"
    transmembrane_name_match = re.search(r"name\s*=\s*(\d+)", normalized)
    if transmembrane_name_match:
        return f"TM{transmembrane_name_match.group(1)}"
    short_labels = (
        ("dynamin-type g", "GTPase"),
        ("rpe65 catalytic", "RPE65 cat."),
        ("carotenoid oxygenase", "RPE65 cat."),
        ("frizzled cysteine-rich", "CRD"),
        ("frizzled domain", "Fz"),
        ("wnt-binding", "CRD"),
        ("wnt binding", "CRD"),
        ("transmembrane helix", "TM"),
        ("signal peptide", "SP"),
        ("extracellular", "Extra"),
        ("cytoplasmic", "Cyto"),
        ("iron-binding", "Fe"),
        ("palmitoyl", "Palm"),
        ("membrane contact", "Mem"),
        ("pleckstrin homology", "PH"),
        ("gtpase effector", "GED"),
        ("proline-rich", "PRD"),
        ("proline rich", "PRD"),
        ("nuclear localization signal", "NLS"),
        ("gtpase", "GTPase"),
        ("middle/stalk", "Middle"),
        ("middle domain", "Middle"),
        ("laminin egf", "LamEGF"),
        ("laminin g", "LamG"),
        ("laminin n", "LamNT"),
        ("fibronectin type-iii", "FN3"),
        ("fibronectin type iii", "FN3"),
        ("coiled-coil", "CC"),
        ("helical", "TM"),
        ("carotenoid oxygenase", "COX"),
    )
    for needle, abbreviation in short_labels:
        if needle in normalized:
            return abbreviation
    if len(label) <= 12:
        return label
    words = re.findall(r"[A-Za-z0-9]+", label)
    if 1 < len(words) <= 4:
        acronym = "".join(word[0].upper() for word in words if word)
        if 2 <= len(acronym) <= 6:
            return acronym
    return label[:12].rstrip()


def _uniprot_feature_description(label: str) -> str:
    normalized = label.lower()
    if normalized == "fz" or "frizzled cysteine-rich" in normalized:
        return "WNT-binding Frizzled cysteine-rich domain"
    if "rpe65" in normalized and "carotenoid oxygenase" in normalized:
        return "Carotenoid oxygenase/RPE65 catalytic family domain"
    return label


def _uniprot_feature_lane(kind: str) -> str:
    if kind in {"signal_peptide", "transmembrane", "topological_domain"}:
        return "topology"
    if kind in {"site", "epitope"}:
        return "sites"
    if kind in {"motif", "coiled_coil", "low_complexity"}:
        return "motifs"
    return "domains"


def _protein_track_provenance(registry: DataSourceRegistry) -> list[ProteinTrackProvenance]:
    source_ids = (
        "uniprotkb_reviewed_swissprot",
        "interpro_pfam_protein_matches",
        "hmmer_pfam_a",
    )
    provenance: list[ProteinTrackProvenance] = []
    for source_id in source_ids:
        record = registry.get(source_id)
        asset = _first_asset_for_source(source_id)
        provenance.append(
            ProteinTrackProvenance(
                source_id=source_id,
                source_name=record.display_name,
                source_url=record.source_url,
                source_release=record.source_version,
                checksum_md5=asset.expected_md5 if asset is not None else record.current_local_md5,
                checksum_sha256=asset.expected_sha256 if asset is not None else None,
                license_status=record.license_status.value,
            )
        )
    return provenance


def _first_asset_for_source(source_id: str) -> ProteinAssetSpec | None:
    return next(
        (asset for asset in PROTEIN_ANNOTATION_ASSETS if source_id in asset.source_ids), None
    )


def _asset_sha256(asset_id: str) -> str | None:
    return next(
        (
            asset.expected_sha256
            for asset in PROTEIN_ANNOTATION_ASSETS
            if asset.asset_id == asset_id
        ),
        None,
    )


def _unavailable_track(
    reason: str,
    *,
    protein_length: int | None = None,
    sequence_hash: str | None = None,
    sequence_label: str | None = None,
    gene_symbol: str | None = None,
    transcript: str | None = None,
    protein_accession: str | None = None,
    translated_from: str = "unknown",
    cache_key: str | None = None,
    cache_status: str = "not_used",
    pfam_release: str | None = None,
    hmmer_release: str | None = None,
    uniprot_release: str | None = None,
    warnings: list[str] | None = None,
) -> ProteinDomainTrack:
    return ProteinDomainTrack(
        status="unavailable",
        fail_closed_reason=reason,
        sequence_label=sequence_label,
        gene_symbol=gene_symbol,
        transcript=transcript,
        protein_accession=protein_accession,
        protein_length=protein_length,
        protein_sequence_hash=sequence_hash,
        translated_from=translated_from,
        cache_key=cache_key,
        cache_status=cache_status,
        pfam_release=pfam_release,
        hmmer_release=hmmer_release,
        uniprot_release=uniprot_release,
        warnings=_dedupe([*(warnings or []), reason]),
    )


def _cache_key(
    *,
    sequence_hash: str,
    pfam_release: str,
    hmmer_release: str,
    uniprot_release: str | None,
) -> str:
    key = f"protein_annotation:sha256:{sequence_hash}:pfam:{pfam_release}:hmmer:{hmmer_release}"
    if uniprot_release:
        key = f"{key}:uniprot:{uniprot_release}"
    return key


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _dedupe_features(
    features: list[ProteinDomainTrackFeature],
) -> list[ProteinDomainTrackFeature]:
    seen: set[tuple[str, int, int, str]] = set()
    result: list[ProteinDomainTrackFeature] = []
    for feature in features:
        key = (feature.accession or feature.label, feature.aa_start, feature.aa_end, feature.kind)
        if key in seen:
            continue
        seen.add(key)
        result.append(feature)
    return result


def _sha256_text(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


def resolve_protein_runtime_path(settings: Settings, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


def resolve_executable(path: Path) -> str | None:
    return shutil.which(str(path))
