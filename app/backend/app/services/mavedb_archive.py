from __future__ import annotations

from collections.abc import Iterator
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import TextIOWrapper
import json
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

_EXPERIMENT_SET_URN_RE = re.compile(r"urn:mavedb:[0-9]{8}")
_EXPERIMENT_URN_RE = re.compile(r"urn:mavedb:[0-9]{8}-(?:[a-z]+|0)")
_SCORE_SET_URN_RE = re.compile(r"urn:mavedb:[0-9]{8}-(?:[a-z]+|0)-[1-9][0-9]*")
_VARIANT_URN_RE = re.compile(r"urn:mavedb:[0-9]{8}-(?:[a-z]+|0)-[1-9][0-9]*#[1-9][0-9]*")
_CSV_MEMBER_RE = re.compile(
    r"(?P<urn>urn:mavedb:[0-9]{8}-(?:[a-z]+|0)-[1-9][0-9]*)"
    r"(?:(?:[._-])(?P<kind>scores?|counts?))?\.csv"
)
_DOI_RE = re.compile(r"10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+")
_FIXED_VARIANT_COLUMNS = frozenset(
    {"urn", "variant_urn", "hgvs_nt", "hgvs_splice", "hgvs_pro", "guide_sequence"}
)
_OPTIONAL_MAPPING_COLUMNS = frozenset(
    {
        "vrs_id",
        "ga4gh_vrs_id",
        "mapped_vrs_id",
        "genomic_identity",
        "genomic_hgvs",
        "mapped_hgvs",
        "mapping_assembly",
        "assembly",
    }
)
_MISSING_NUMERIC_VALUES = frozenset({"", "na", "nan", "null", "none"})
_CSV_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_METADATA_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class MaveDbArchiveLimits:
    max_members: int = 50_000
    max_filename_bytes: int = 240
    max_compressed_bytes: int = 2_500_000_000
    max_expanded_bytes: int = 64 * 1024 * 1024 * 1024
    max_member_expanded_bytes: int = 16 * 1024 * 1024 * 1024
    max_compression_ratio: int = 200
    max_main_json_bytes: int = 256 * 1024 * 1024
    max_rows: int = 100_000_000
    max_columns: int = 512
    max_cell_bytes: int = 256 * 1024
    max_line_bytes: int = 2 * 1024 * 1024
    max_metadata_text_bytes: int = 512 * 1024
    max_target_sequence_bytes: int = 16 * 1024 * 1024
    max_identifiers: int = 128


DEFAULT_MAVEDB_ARCHIVE_LIMITS = MaveDbArchiveLimits()


@dataclass(frozen=True)
class MaveDbArchiveColumn:
    name: str
    description: str | None = None
    details: str | None = None


@dataclass(frozen=True)
class MaveDbArchiveTarget:
    target_id: str
    target_kind: str
    target_accession: str | None
    target_assembly: str | None
    target_sequence_checksum: str
    gene: str | None
    label: str | None

    @property
    def exact_identity(self) -> str:
        return "|".join(
            (
                self.target_kind,
                self.target_accession or "",
                self.target_assembly or "",
                self.target_sequence_checksum,
            )
        )


@dataclass(frozen=True)
class MaveDbArchiveScoreSet:
    score_set_urn: str
    experiment_urn: str
    experiment_set_urn: str
    license_snapshot: str
    data_usage_policy: str | None
    data_usage_policy_decision: str
    deprecated: bool
    superseded_by: str | None
    title: str | None
    short_description: str | None
    score_set_method_text: str | None
    experiment_method_text: str | None
    experiment_short_description: str | None
    doi_identifiers: tuple[str, ...]
    publication_identifiers: tuple[str, ...]
    score_columns: tuple[MaveDbArchiveColumn, ...]
    target: MaveDbArchiveTarget | None
    admission_error: str | None
    expected_variant_count: int | None

    @property
    def assay_context(self) -> str | None:
        return self.short_description or self.experiment_short_description or self.title


@dataclass(frozen=True)
class MaveDbArchiveInventory:
    metadata_schema_version: str
    score_sets: tuple[MaveDbArchiveScoreSet, ...]
    score_files: tuple[tuple[str, str], ...]
    count_files: tuple[tuple[str, str], ...]
    member_count: int
    compressed_bytes: int
    expanded_bytes: int

    def score_set_map(self) -> dict[str, MaveDbArchiveScoreSet]:
        return {record.score_set_urn: record for record in self.score_sets}


@dataclass(frozen=True)
class MaveDbArchiveMemberDigest:
    member_name: str
    expanded_bytes: int
    compressed_bytes: int
    sha256: str


@dataclass(frozen=True)
class MaveDbArchiveNumericValue:
    column: str
    source_value: str
    parsed_value: Decimal
    description: str | None = None
    details: str | None = None


@dataclass(frozen=True)
class MaveDbArchiveScoreRow:
    score_set_urn: str
    variant_urn: str | None
    mave_hgvs_nt: str | None
    mave_hgvs_splice: str | None
    mave_hgvs_pro: str | None
    raw_score_source: str | None
    raw_score: Decimal | None
    uncertainty_values: tuple[MaveDbArchiveNumericValue, ...]
    vrs_id: str | None
    genomic_identity: str | None
    mapping_assembly: str | None
    rejection_code: str | None = None


class MaveDbArchiveError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(f"MaveDB archive rejected: {code}")
        self.code = code


class _AdmissionRejected(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def inspect_mavedb_archive(
    archive_path: Path,
    *,
    limits: MaveDbArchiveLimits = DEFAULT_MAVEDB_ARCHIVE_LIMITS,
) -> MaveDbArchiveInventory:
    try:
        with ZipFile(archive_path, "r") as archive:
            members = _validate_members(archive.infolist(), limits=limits)
            main_info = members.get("main.json")
            if main_info is None:
                raise MaveDbArchiveError("main_json_missing")
            payload = _read_main_json(archive, main_info, limits=limits)
            score_sets, schema_version = _parse_metadata(payload, limits=limits)
    except BadZipFile as exc:
        raise MaveDbArchiveError("invalid_zip") from exc

    score_set_urns = {record.score_set_urn for record in score_sets}
    score_files: dict[str, str] = {}
    count_files: dict[str, str] = {}
    for name in members:
        if name == "main.json":
            continue
        parsed = _csv_member_identity(name)
        if parsed is None:
            raise MaveDbArchiveError("unexpected_member")
        urn, kind = parsed
        if urn not in score_set_urns:
            raise MaveDbArchiveError("csv_without_authoritative_metadata")
        destination = score_files if kind == "score" else count_files
        if urn in destination:
            raise MaveDbArchiveError("duplicate_score_set_csv")
        destination[urn] = name

    for record in score_sets:
        if record.expected_variant_count != 0 and record.score_set_urn not in score_files:
            raise MaveDbArchiveError("score_csv_missing")

    infos = tuple(members.values())
    return MaveDbArchiveInventory(
        metadata_schema_version=schema_version,
        score_sets=score_sets,
        score_files=tuple(sorted(score_files.items())),
        count_files=tuple(sorted(count_files.items())),
        member_count=len(infos),
        compressed_bytes=sum(info.compress_size for info in infos),
        expanded_bytes=sum(info.file_size for info in infos),
    )


def iter_mavedb_archive_score_rows(
    archive_path: Path,
    inventory: MaveDbArchiveInventory,
    *,
    limits: MaveDbArchiveLimits = DEFAULT_MAVEDB_ARCHIVE_LIMITS,
) -> Iterator[MaveDbArchiveScoreRow]:
    score_sets = inventory.score_set_map()
    total_rows = 0
    try:
        with ZipFile(archive_path, "r") as archive:
            members = {info.filename: info for info in archive.infolist()}
            for score_set_urn, member_name in inventory.score_files:
                metadata = score_sets[score_set_urn]
                info = members.get(member_name)
                if info is None:
                    raise MaveDbArchiveError("archive_changed_after_inventory")
                row_count = 0
                with archive.open(info, "r") as raw_handle:
                    text_handle = TextIOWrapper(raw_handle, encoding="utf-8-sig", newline="")
                    lines = _bounded_noncomment_lines(text_handle, limits=limits)
                    try:
                        header = next(lines)
                    except StopIteration as exc:
                        raise MaveDbArchiveError("score_csv_empty") from exc
                    fieldnames = next(csv.reader([header]))
                    _validate_csv_header(fieldnames, metadata=metadata, limits=limits)
                    reader = csv.DictReader(lines, fieldnames=fieldnames, restkey="__extra__")
                    for raw_row in reader:
                        total_rows += 1
                        row_count += 1
                        if total_rows > limits.max_rows:
                            raise MaveDbArchiveError("row_limit_exceeded")
                        yield _parse_score_row(
                            raw_row,
                            metadata=metadata,
                            limits=limits,
                        )
                if (
                    metadata.expected_variant_count is not None
                    and row_count != metadata.expected_variant_count
                ):
                    raise MaveDbArchiveError("variant_count_mismatch")
    except BadZipFile as exc:
        raise MaveDbArchiveError("invalid_zip") from exc
    except (UnicodeDecodeError, csv.Error) as exc:
        raise MaveDbArchiveError("score_csv_invalid") from exc


def iter_mavedb_archive_member_digests(
    archive_path: Path,
    *,
    limits: MaveDbArchiveLimits = DEFAULT_MAVEDB_ARCHIVE_LIMITS,
) -> Iterator[MaveDbArchiveMemberDigest]:
    try:
        with ZipFile(archive_path, "r") as archive:
            members = _validate_members(archive.infolist(), limits=limits)
            for member_name, info in sorted(members.items()):
                digest = sha256()
                expanded_bytes = 0
                with archive.open(info, "r") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        expanded_bytes += len(chunk)
                        if expanded_bytes > info.file_size:
                            raise MaveDbArchiveError("member_expanded_size_mismatch")
                        digest.update(chunk)
                if expanded_bytes != info.file_size:
                    raise MaveDbArchiveError("member_expanded_size_mismatch")
                yield MaveDbArchiveMemberDigest(
                    member_name=member_name,
                    expanded_bytes=expanded_bytes,
                    compressed_bytes=info.compress_size,
                    sha256=digest.hexdigest(),
                )
    except BadZipFile as exc:
        raise MaveDbArchiveError("invalid_zip") from exc


def _validate_members(
    infos: list[ZipInfo],
    *,
    limits: MaveDbArchiveLimits,
) -> dict[str, ZipInfo]:
    if not infos or len(infos) > limits.max_members:
        raise MaveDbArchiveError("member_count_out_of_bounds")
    members: dict[str, ZipInfo] = {}
    compressed_bytes = 0
    expanded_bytes = 0
    for info in infos:
        name = info.filename
        if (
            not name
            or "\x00" in name
            or len(name.encode("utf-8")) > limits.max_filename_bytes
            or "\\" in name
        ):
            raise MaveDbArchiveError("unsafe_member_name")
        path = PurePosixPath(name)
        if path.is_absolute() or len(path.parts) != 1 or path.name in {".", ".."}:
            raise MaveDbArchiveError("unsafe_member_path")
        if name in members:
            raise MaveDbArchiveError("duplicate_member_name")
        if info.is_dir() or info.flag_bits & 0x1:
            raise MaveDbArchiveError("unsupported_member_type")
        mode = info.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        if file_type not in {0, stat.S_IFREG}:
            raise MaveDbArchiveError("unsupported_member_type")
        if info.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
            raise MaveDbArchiveError("unsupported_compression")
        if info.file_size < 0 or info.file_size > limits.max_member_expanded_bytes:
            raise MaveDbArchiveError("member_size_out_of_bounds")
        if info.file_size > 0 and info.compress_size <= 0:
            raise MaveDbArchiveError("invalid_compression_size")
        if (
            info.compress_size > 0
            and info.file_size / info.compress_size > limits.max_compression_ratio
        ):
            raise MaveDbArchiveError("compression_ratio_exceeded")
        compressed_bytes += info.compress_size
        expanded_bytes += info.file_size
        if compressed_bytes > limits.max_compressed_bytes:
            raise MaveDbArchiveError("compressed_size_limit_exceeded")
        if expanded_bytes > limits.max_expanded_bytes:
            raise MaveDbArchiveError("expanded_size_limit_exceeded")
        members[name] = info
    return members


def _read_main_json(
    archive: ZipFile,
    info: ZipInfo,
    *,
    limits: MaveDbArchiveLimits,
) -> Any:
    if info.file_size > limits.max_main_json_bytes:
        raise MaveDbArchiveError("main_json_too_large")
    with archive.open(info, "r") as handle:
        encoded = handle.read(limits.max_main_json_bytes + 1)
    if len(encoded) > limits.max_main_json_bytes:
        raise MaveDbArchiveError("main_json_too_large")
    try:
        return json.loads(
            encoded.decode("utf-8-sig"),
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")),
            object_pairs_hook=_unique_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise MaveDbArchiveError("main_json_invalid") from exc


def _parse_metadata(
    payload: Any,
    *,
    limits: MaveDbArchiveLimits,
) -> tuple[tuple[MaveDbArchiveScoreSet, ...], str]:
    experiment_sets, experiments, score_sets, schema_version = _metadata_records(
        payload,
        limits=limits,
    )
    experiment_set_map = _unique_by_urn(experiment_sets, "experiment_set")
    experiment_map = _unique_by_urn(experiments, "experiment")
    score_set_map = _unique_by_urn(score_sets, "score_set")
    if not score_set_map:
        raise MaveDbArchiveError("score_set_metadata_missing")

    parsed = tuple(
        _parse_score_set_metadata(
            raw,
            experiment_map=experiment_map,
            experiment_set_map=experiment_set_map,
            limits=limits,
        )
        for _, raw in sorted(score_set_map.items())
    )
    return parsed, schema_version


def _metadata_records(
    payload: Any,
    *,
    limits: MaveDbArchiveLimits,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    experiment_sets: list[dict[str, Any]] = []
    experiments: list[dict[str, Any]] = []
    score_sets: list[dict[str, Any]] = []
    schema_version = "mavedb_bulk_main_json_unversioned"

    if isinstance(payload, dict):
        schema_value = _optional_bounded_text(
            payload.get("schemaVersion") or payload.get("schema_version"),
            min(limits.max_metadata_text_bytes, 256),
        )
        if schema_value is not None:
            schema_version = schema_value
        for key, destination in (
            ("experimentSets", experiment_sets),
            ("experiment_sets", experiment_sets),
            ("experiments", experiments),
            ("scoreSets", score_sets),
            ("score_sets", score_sets),
        ):
            value = payload.get(key)
            if isinstance(value, list):
                destination.extend(item for item in value if isinstance(item, dict))
        records = payload.get("records")
        if isinstance(records, list):
            _classify_records(records, experiment_sets, experiments, score_sets)
    elif isinstance(payload, list):
        _classify_records(payload, experiment_sets, experiments, score_sets)
    else:
        raise MaveDbArchiveError("main_json_shape_unsupported")

    for experiment_set in tuple(experiment_sets):
        nested_experiments = experiment_set.get("experiments")
        if isinstance(nested_experiments, list):
            for experiment in nested_experiments:
                if not isinstance(experiment, dict):
                    continue
                enriched = dict(experiment)
                enriched.setdefault("experimentSetUrn", experiment_set.get("urn"))
                experiments.append(enriched)
    for experiment in tuple(experiments):
        nested_score_sets = experiment.get("scoreSets") or experiment.get("score_sets")
        if isinstance(nested_score_sets, list):
            for score_set in nested_score_sets:
                if not isinstance(score_set, dict):
                    continue
                enriched = dict(score_set)
                enriched.setdefault("experimentUrn", experiment.get("urn"))
                score_sets.append(enriched)
    for score_set in tuple(score_sets):
        nested_experiment = score_set.get("experiment")
        if isinstance(nested_experiment, dict):
            experiments.append(nested_experiment)

    return experiment_sets, experiments, score_sets, schema_version


def _classify_records(
    records: list[Any],
    experiment_sets: list[dict[str, Any]],
    experiments: list[dict[str, Any]],
    score_sets: list[dict[str, Any]],
) -> None:
    for item in records:
        if not isinstance(item, dict):
            continue
        record_type = re.sub(r"[^a-z]", "", str(item.get("recordType") or "").lower())
        if record_type == "experimentset":
            experiment_sets.append(item)
        elif record_type == "experiment":
            experiments.append(item)
        elif record_type == "scoreset":
            score_sets.append(item)


def _unique_by_urn(
    records: list[dict[str, Any]],
    record_kind: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        urn = _optional_bounded_text(record.get("urn"), 160)
        if urn is None:
            continue
        existing = result.get(urn)
        if existing is None:
            result[urn] = record
            continue
        merged = dict(existing)
        for key, value in record.items():
            prior = merged.get(key)
            if (
                prior not in (None, "", [], {})
                and value not in (None, "", [], {})
                and prior != value
            ):
                raise MaveDbArchiveError(f"conflicting_{record_kind}_metadata")
            if prior in (None, "", [], {}):
                merged[key] = value
        result[urn] = merged
    return result


def _parse_score_set_metadata(
    raw: dict[str, Any],
    *,
    experiment_map: dict[str, dict[str, Any]],
    experiment_set_map: dict[str, dict[str, Any]],
    limits: MaveDbArchiveLimits,
) -> MaveDbArchiveScoreSet:
    score_set_urn = _required_bounded_text(raw.get("urn"), 160, "score_set_urn_missing")
    if not _SCORE_SET_URN_RE.fullmatch(score_set_urn):
        raise MaveDbArchiveError("score_set_urn_invalid")

    nested_experiment = raw.get("experiment") if isinstance(raw.get("experiment"), dict) else {}
    experiment_urn = (
        _optional_bounded_text(raw.get("experimentUrn") or nested_experiment.get("urn"), 160)
        or score_set_urn.rsplit("-", 1)[0]
    )
    if not _EXPERIMENT_URN_RE.fullmatch(experiment_urn):
        raise MaveDbArchiveError("experiment_urn_invalid")
    experiment = experiment_map.get(experiment_urn, nested_experiment)
    experiment_set_urn = _optional_bounded_text(experiment.get("experimentSetUrn"), 160)
    if experiment_set_urn is None:
        experiment_set_urn = experiment_urn.rsplit("-", 1)[0]
    if not _EXPERIMENT_SET_URN_RE.fullmatch(experiment_set_urn):
        raise MaveDbArchiveError("experiment_set_urn_invalid")
    if score_set_urn.rsplit("-", 1)[0] != experiment_urn:
        raise MaveDbArchiveError("score_set_experiment_hierarchy_mismatch")
    if experiment_urn.rsplit("-", 1)[0] != experiment_set_urn:
        raise MaveDbArchiveError("experiment_set_hierarchy_mismatch")
    if experiment_set_urn in experiment_set_map:
        _ = experiment_set_map[experiment_set_urn]

    license_snapshot = _license_snapshot(raw.get("license"), limits=limits)
    data_usage_policy = _optional_bounded_text(
        raw.get("dataUsagePolicy"), limits.max_metadata_text_bytes
    )
    policy_decision = (
        "no_additional_restriction"
        if data_usage_policy is None
        else "restricted_or_ambiguous_policy"
    )
    superseded_by = _related_score_set_urn(
        raw.get("supersedingScoreSet") or raw.get("superseded_by")
    )
    deprecated = bool(raw.get("deprecated", False) or superseded_by)

    target: MaveDbArchiveTarget | None = None
    admission_error: str | None = None
    try:
        target = _parse_target(raw.get("targetGenes"), score_set_urn, limits=limits)
        if bool(raw.get("private", False)):
            raise _AdmissionRejected("private_score_set_rejected")
    except _AdmissionRejected as exc:
        admission_error = exc.code

    score_columns: tuple[MaveDbArchiveColumn, ...] = ()
    try:
        score_columns = _parse_score_columns(raw.get("datasetColumns"), limits=limits)
    except _AdmissionRejected as exc:
        admission_error = admission_error or exc.code

    expected_variant_count = raw.get("numVariants")
    if expected_variant_count is not None:
        if (
            isinstance(expected_variant_count, bool)
            or not isinstance(expected_variant_count, int)
            or expected_variant_count < 0
            or expected_variant_count > limits.max_rows
        ):
            raise MaveDbArchiveError("num_variants_invalid")

    return MaveDbArchiveScoreSet(
        score_set_urn=score_set_urn,
        experiment_urn=experiment_urn,
        experiment_set_urn=experiment_set_urn,
        license_snapshot=license_snapshot,
        data_usage_policy=data_usage_policy,
        data_usage_policy_decision=policy_decision,
        deprecated=deprecated,
        superseded_by=superseded_by,
        title=_optional_bounded_text(raw.get("title"), limits.max_metadata_text_bytes),
        short_description=_optional_bounded_text(
            raw.get("shortDescription"), limits.max_metadata_text_bytes
        ),
        score_set_method_text=_optional_bounded_text(
            raw.get("methodText"), limits.max_metadata_text_bytes
        ),
        experiment_method_text=_optional_bounded_text(
            experiment.get("methodText"), limits.max_metadata_text_bytes
        ),
        experiment_short_description=_optional_bounded_text(
            experiment.get("shortDescription"), limits.max_metadata_text_bytes
        ),
        doi_identifiers=_identifier_values(
            [raw.get("doiIdentifiers"), experiment.get("doiIdentifiers")],
            kind="doi",
            limits=limits,
        ),
        publication_identifiers=_identifier_values(
            [
                raw.get("primaryPublicationIdentifiers"),
                raw.get("secondaryPublicationIdentifiers"),
                experiment.get("primaryPublicationIdentifiers"),
                experiment.get("secondaryPublicationIdentifiers"),
            ],
            kind="publication",
            limits=limits,
        ),
        score_columns=score_columns,
        target=target,
        admission_error=admission_error,
        expected_variant_count=expected_variant_count,
    )


def _parse_target(
    value: Any,
    score_set_urn: str,
    *,
    limits: MaveDbArchiveLimits,
) -> MaveDbArchiveTarget:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise _AdmissionRejected("ambiguous_or_missing_target_rejected")
    raw = value[0]
    accession_raw = raw.get("targetAccession")
    sequence_raw = raw.get("targetSequence")
    has_accession = isinstance(accession_raw, dict)
    has_sequence = isinstance(sequence_raw, dict)
    if has_accession == has_sequence:
        raise _AdmissionRejected("ambiguous_target_kind_rejected")

    raw_id = raw.get("id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, int | str):
        raise _AdmissionRejected("target_id_missing")
    target_id = f"{score_set_urn}:target:{raw_id}"
    gene = _optional_bounded_text(
        raw.get("mappedHgncName") or raw.get("name"), limits.max_metadata_text_bytes
    )
    label = _optional_bounded_text(raw.get("name"), limits.max_metadata_text_bytes)

    if has_accession:
        assert isinstance(accession_raw, dict)
        accession = _optional_bounded_text(accession_raw.get("accession"), 160)
        if accession is None or not re.fullmatch(r"[A-Za-z0-9_:-]+\.[0-9]+", accession):
            raise _AdmissionRejected("unversioned_target_accession_rejected")
        assembly = _optional_bounded_text(accession_raw.get("assembly"), 128)
        gene = _optional_bounded_text(accession_raw.get("gene"), 256) or gene
        checksum = sha256(
            f"accession:{accession}|assembly:{assembly or ''}".encode("utf-8")
        ).hexdigest()
        return MaveDbArchiveTarget(
            target_id=target_id,
            target_kind="accession",
            target_accession=accession,
            target_assembly=assembly,
            target_sequence_checksum=f"sha256:{checksum}",
            gene=gene,
            label=label,
        )

    assert isinstance(sequence_raw, dict)
    sequence = _optional_bounded_text(
        sequence_raw.get("sequence"), limits.max_target_sequence_bytes
    )
    if sequence is None or not re.fullmatch(r"[A-Za-z*]+", sequence):
        raise _AdmissionRejected("target_sequence_invalid")
    checksum = sha256(sequence.upper().encode("ascii")).hexdigest()
    return MaveDbArchiveTarget(
        target_id=target_id,
        target_kind="sequence",
        target_accession=None,
        target_assembly=None,
        target_sequence_checksum=f"sha256:{checksum}",
        gene=gene,
        label=label,
    )


def _parse_score_columns(
    value: Any,
    *,
    limits: MaveDbArchiveLimits,
) -> tuple[MaveDbArchiveColumn, ...]:
    if not isinstance(value, dict):
        raise _AdmissionRejected("score_column_metadata_missing")
    names = value.get("scoreColumns")
    if not isinstance(names, list) or not names or len(names) > limits.max_columns:
        raise _AdmissionRejected("score_columns_invalid")
    metadata = value.get("scoreColumnsMetadata")
    metadata_map = metadata if isinstance(metadata, dict) else {}
    parsed: list[MaveDbArchiveColumn] = []
    seen: set[str] = set()
    for raw_name in names:
        name = _optional_bounded_text(raw_name, 256)
        if name is None or name in seen:
            raise _AdmissionRejected("score_columns_invalid")
        seen.add(name)
        raw_metadata = metadata_map.get(name)
        raw_metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        parsed.append(
            MaveDbArchiveColumn(
                name=name,
                description=_optional_bounded_text(
                    raw_metadata.get("description"), limits.max_metadata_text_bytes
                ),
                details=_optional_bounded_text(
                    raw_metadata.get("details"), limits.max_metadata_text_bytes
                ),
            )
        )
    if "score" not in seen:
        raise _AdmissionRejected("required_score_column_missing")
    return tuple(parsed)


def _license_snapshot(value: Any, *, limits: MaveDbArchiveLimits) -> str:
    if not isinstance(value, dict):
        return "unknown"
    short_name = _optional_bounded_text(value.get("shortName"), 128)
    version = _optional_bounded_text(value.get("version"), 64)
    if short_name is None:
        return "unknown"
    return f"{short_name}-{version}" if version else short_name


def _related_score_set_urn(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("urn")
    urn = _optional_bounded_text(value, 160)
    if urn is not None and not _SCORE_SET_URN_RE.fullmatch(urn):
        raise MaveDbArchiveError("superseding_score_set_urn_invalid")
    return urn


def _identifier_values(
    groups: list[Any],
    *,
    kind: str,
    limits: MaveDbArchiveLimits,
) -> tuple[str, ...]:
    values: list[str] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            if len(values) >= limits.max_identifiers:
                raise MaveDbArchiveError("identifier_count_exceeded")
            if not isinstance(item, dict):
                continue
            identifier = _optional_bounded_text(item.get("identifier"), 512)
            if identifier is None:
                continue
            if kind == "doi":
                if not _DOI_RE.fullmatch(identifier):
                    continue
                normalized = identifier
            else:
                db_name = _optional_bounded_text(item.get("dbName"), 64)
                if db_name and db_name.casefold() in {"pubmed", "pmid"}:
                    if not identifier.isdigit():
                        continue
                    normalized = f"PMID:{identifier}"
                elif _DOI_RE.fullmatch(identifier):
                    normalized = f"DOI:{identifier}"
                else:
                    normalized = f"{db_name}:{identifier}" if db_name else identifier
            if normalized not in values:
                values.append(normalized)
    return tuple(values)


def _csv_member_identity(name: str) -> tuple[str, str] | None:
    match = _CSV_MEMBER_RE.fullmatch(name)
    if match is None:
        return None
    kind = (match.group("kind") or "score").casefold()
    return match.group("urn"), "count" if kind.startswith("count") else "score"


def _bounded_noncomment_lines(
    handle: TextIOWrapper,
    *,
    limits: MaveDbArchiveLimits,
) -> Iterator[str]:
    while True:
        line = handle.readline(limits.max_line_bytes + 1)
        if not line:
            return
        if len(line.encode("utf-8")) > limits.max_line_bytes:
            raise MaveDbArchiveError("csv_line_too_large")
        if line.lstrip().startswith("#") or not line.strip():
            continue
        yield line


def _validate_csv_header(
    fieldnames: list[str],
    *,
    metadata: MaveDbArchiveScoreSet,
    limits: MaveDbArchiveLimits,
) -> None:
    if (
        not fieldnames
        or len(fieldnames) > limits.max_columns
        or len(fieldnames) != len(set(fieldnames))
        or any(
            not name
            or len(name.encode("utf-8")) > limits.max_cell_bytes
            or _CSV_CONTROL_RE.search(name)
            for name in fieldnames
        )
    ):
        raise MaveDbArchiveError("score_csv_header_invalid")
    variant_urn_columns = {"urn", "variant_urn"}.intersection(fieldnames)
    if len(variant_urn_columns) != 1 or "score" not in fieldnames:
        raise MaveDbArchiveError("score_csv_required_columns_missing")
    if not {"hgvs_nt", "hgvs_pro", "guide_sequence"}.intersection(fieldnames):
        raise MaveDbArchiveError("score_csv_variant_identity_missing")
    declared = {column.name for column in metadata.score_columns}
    allowed = _FIXED_VARIANT_COLUMNS | _OPTIONAL_MAPPING_COLUMNS | declared
    if set(fieldnames) - allowed:
        raise MaveDbArchiveError("score_csv_undeclared_columns")
    if declared - set(fieldnames):
        raise MaveDbArchiveError("score_csv_declared_columns_missing")


def _parse_score_row(
    raw: dict[str, Any],
    *,
    metadata: MaveDbArchiveScoreSet,
    limits: MaveDbArchiveLimits,
) -> MaveDbArchiveScoreRow:
    if raw.get("__extra__"):
        raise MaveDbArchiveError("score_csv_row_width_mismatch")
    if any(
        value is not None and len(str(value).encode("utf-8")) > limits.max_cell_bytes
        for key, value in raw.items()
        if key != "__extra__"
    ):
        raise MaveDbArchiveError("score_csv_cell_too_large")
    if any(
        value is not None and _CSV_CONTROL_RE.search(str(value))
        for key, value in raw.items()
        if key != "__extra__"
    ):
        raise MaveDbArchiveError("score_csv_control_character_rejected")

    variant_urn = _first_text(raw, ("urn", "variant_urn"))
    hgvs_nt = _optional_cell(raw.get("hgvs_nt"))
    hgvs_splice = _optional_cell(raw.get("hgvs_splice"))
    hgvs_pro = _optional_cell(raw.get("hgvs_pro"))
    score_source = _optional_numeric_source(raw.get("score"))
    score = _decimal_or_none(score_source)
    rejection_code: str | None = None
    if variant_urn is None or not _VARIANT_URN_RE.fullmatch(variant_urn):
        rejection_code = "variant_urn_invalid"
    elif not hgvs_nt and not hgvs_pro:
        rejection_code = "variant_hgvs_missing"
    elif score_source is None or score is None:
        rejection_code = "raw_score_missing_or_invalid"

    column_map = {column.name: column for column in metadata.score_columns}
    extra_values: list[MaveDbArchiveNumericValue] = []
    for column_name, column in column_map.items():
        if column_name == "score":
            continue
        source_value = _optional_numeric_source(raw.get(column_name))
        if source_value is None:
            continue
        parsed = _decimal_or_none(source_value)
        if parsed is None:
            rejection_code = rejection_code or "additional_score_value_invalid"
            continue
        extra_values.append(
            MaveDbArchiveNumericValue(
                column=column_name,
                source_value=source_value,
                parsed_value=parsed,
                description=column.description,
                details=column.details,
            )
        )

    return MaveDbArchiveScoreRow(
        score_set_urn=metadata.score_set_urn,
        variant_urn=variant_urn,
        mave_hgvs_nt=hgvs_nt,
        mave_hgvs_splice=hgvs_splice,
        mave_hgvs_pro=hgvs_pro,
        raw_score_source=score_source,
        raw_score=score,
        uncertainty_values=tuple(extra_values),
        vrs_id=_single_consistent_text(raw, ("vrs_id", "ga4gh_vrs_id", "mapped_vrs_id")),
        genomic_identity=_single_consistent_text(
            raw, ("genomic_identity", "genomic_hgvs", "mapped_hgvs")
        ),
        mapping_assembly=_single_consistent_text(raw, ("mapping_assembly", "assembly")),
        rejection_code=rejection_code,
    )


def _single_consistent_text(raw: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    values = {_optional_cell(raw.get(key)) for key in keys}
    values.discard(None)
    if len(values) > 1:
        raise MaveDbArchiveError("conflicting_mapping_columns")
    return next(iter(values), None)


def _first_text(raw: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _optional_cell(raw.get(key))
        if value is not None:
            return value
    return None


def _optional_cell(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return None if text.strip().casefold() in _MISSING_NUMERIC_VALUES else text.strip()


def _optional_numeric_source(value: Any) -> str | None:
    if value is None:
        return None
    source = str(value)
    return None if source.strip().casefold() in _MISSING_NUMERIC_VALUES else source


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value.strip())
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _required_bounded_text(value: Any, maximum: int, code: str) -> str:
    text = _optional_bounded_text(value, maximum)
    if text is None:
        raise MaveDbArchiveError(code)
    return text


def _optional_bounded_text(value: Any, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MaveDbArchiveError("metadata_text_type_invalid")
    text = value.strip()
    if not text:
        return None
    if _METADATA_CONTROL_RE.search(text):
        raise MaveDbArchiveError("metadata_control_character_rejected")
    if len(text.encode("utf-8")) > maximum:
        raise MaveDbArchiveError("metadata_text_too_large")
    return text


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
