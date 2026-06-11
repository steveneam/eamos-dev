from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations, product
from pathlib import Path

from app.schemas.workbench import (
    CrisprOffTargetLocus,
    CrisprOffTargetRequest,
    CrisprOffTargetResponse,
    CrisprOffTargetSite,
)
from app.services.crispr_design import (
    SPCAS9_PAM_LENGTH,
    SPCAS9_SPACER_LENGTH,
    SPCAS9_TARGET_LENGTH,
    clean_dna,
    hsu_mismatch_positions,
    hsu_off_target_cutting_score,
    is_spcas9_pam,
    reverse_complement,
)
from app.services.sequence_context import unsupported_input_warning

CRISPR_OFFTARGET_INDEX_SOURCE_ID = "eamos_crispr_spcas9_offtarget_index"
CRISPR_OFFTARGET_INDEX_SCHEMA_VERSION = "eamos.crispr_spcas9_offtargets.v1"
DEFAULT_INDEX_MAX_MISMATCHES_SUPPORTED = 3
SQLITE_BIND_CHUNK_SIZE = 800


class CrisprOffTargetIndexUnavailable(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CrisprOffTargetIndexUnsupported(Exception):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CrisprOffTargetIndexInspection:
    ready: bool
    status: str
    schema_version: str | None
    genome_build: str | None
    target_count: int
    max_mismatches_supported: int | None
    actual_size_bytes: int | None
    source_id: str = CRISPR_OFFTARGET_INDEX_SOURCE_ID

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "ready": self.ready,
            "status": self.status,
            "schema_version": self.schema_version,
            "genome_build": self.genome_build,
            "target_count": self.target_count,
            "max_mismatches_supported": self.max_mismatches_supported,
            "actual_size_bytes": self.actual_size_bytes,
            "request_time_supabase_search": False,
            "request_time_materialization_allowed": False,
            "startup_materialization_allowed": False,
            "reader_requires_local_path": True,
            "local_path_values_emitted": False,
        }


def inspect_crispr_offtarget_index(index_path: Path | str) -> CrisprOffTargetIndexInspection:
    path = Path(index_path)
    if not path.is_file():
        return CrisprOffTargetIndexInspection(
            ready=False,
            status="missing",
            schema_version=None,
            genome_build=None,
            target_count=0,
            max_mismatches_supported=None,
            actual_size_bytes=None,
        )

    try:
        actual_size_bytes = path.stat().st_size
    except OSError:
        actual_size_bytes = None

    try:
        with _connect_readonly(path) as conn:
            metadata = _metadata(conn)
            schema_version = metadata.get("schema_version")
            target_count = _metadata_int(metadata, "target_count")
            if target_count is None:
                target_count = _target_count(conn)
            genome_build = metadata.get("genome_build")
            max_mismatches_supported = _metadata_int(
                metadata,
                "max_mismatches_supported",
            )
    except sqlite3.Error:
        return CrisprOffTargetIndexInspection(
            ready=False,
            status="invalid_sqlite",
            schema_version=None,
            genome_build=None,
            target_count=0,
            max_mismatches_supported=None,
            actual_size_bytes=actual_size_bytes,
        )

    ready = (
        schema_version == CRISPR_OFFTARGET_INDEX_SCHEMA_VERSION
        and target_count > 0
        and bool(genome_build)
    )
    return CrisprOffTargetIndexInspection(
        ready=ready,
        status="ready" if ready else "incompatible",
        schema_version=schema_version,
        genome_build=genome_build,
        target_count=target_count,
        max_mismatches_supported=max_mismatches_supported,
        actual_size_bytes=actual_size_bytes,
    )


def build_spcas9_offtarget_index_from_sequences(
    records: Iterable[tuple[str, str]],
    output_path: Path | str,
    *,
    genome_build: str = "GRCh38",
    source_version: str | None = None,
    max_mismatches_supported: int = DEFAULT_INDEX_MAX_MISMATCHES_SUPPORTED,
    batch_size: int = 50_000,
) -> CrisprOffTargetIndexInspection:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    try:
        tmp_path.unlink()
    except FileNotFoundError:
        pass

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=MEMORY")
        _create_schema(conn)
        _write_metadata(
            conn,
            {
                "schema_version": CRISPR_OFFTARGET_INDEX_SCHEMA_VERSION,
                "source_id": CRISPR_OFFTARGET_INDEX_SOURCE_ID,
                "genome_build": genome_build,
                "source_version": source_version or "",
                "built_at": now,
                "max_mismatches_supported": str(max_mismatches_supported),
                "target_count": "0",
            },
        )
        target_count = 0
        batch: list[tuple[str, str, str, str, int, None, None, None]] = []
        for chromosome, sequence in records:
            chrom = _normalize_chromosome(chromosome)
            for spacer, pam, strand, position in _iter_spcas9_targets(sequence):
                batch.append((spacer, pam, chrom, strand, position, None, None, None))
                if len(batch) >= batch_size:
                    _insert_targets(conn, batch)
                    target_count += len(batch)
                    batch.clear()
        if batch:
            _insert_targets(conn, batch)
            target_count += len(batch)
        _write_metadata(conn, {"target_count": str(target_count)})
        conn.execute("CREATE INDEX idx_crispr_targets_spacer ON targets(spacer)")
        conn.execute(
            "CREATE INDEX idx_crispr_targets_locus ON targets(chromosome, position, strand)"
        )
        conn.commit()
    finally:
        conn.close()

    os.replace(tmp_path, path)
    return inspect_crispr_offtarget_index(path)


def iter_fasta_records(fasta_path: Path | str) -> Iterator[tuple[str, str]]:
    header: str | None = None
    sequence_parts: list[str] = []
    with Path(fasta_path).open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(sequence_parts)
                header = line[1:].split(maxsplit=1)[0]
                sequence_parts = []
                continue
            sequence_parts.append(line)
    if header is not None:
        yield header, "".join(sequence_parts)


def iter_twobit_records(twobit_path: Path | str) -> Iterator[tuple[str, str]]:
    try:
        from twobitreader import TwoBitFile
    except ModuleNotFoundError as exc:
        raise CrisprOffTargetIndexUnavailable(
            "twobitreader is required to build a CRISPR off-target index from 2bit input."
        ) from exc

    genome = TwoBitFile(str(twobit_path))
    for chromosome in genome.keys():
        yield str(chromosome), str(genome[chromosome])


def query_spcas9_offtarget_index(
    index_path: Path | str,
    payload: CrisprOffTargetRequest,
    *,
    max_results: int = 200,
) -> CrisprOffTargetResponse:
    guide = clean_dna(payload.guide)
    _validate_spcas9_payload(payload)
    inspection = inspect_crispr_offtarget_index(index_path)
    if not inspection.ready:
        raise CrisprOffTargetIndexUnavailable(
            f"CRISPR off-target index is not ready: {inspection.status}."
        )
    if _normalize_build(payload.genome_build) != _normalize_build(inspection.genome_build or ""):
        code = unsupported_input_warning("genome_build")
        raise CrisprOffTargetIndexUnsupported(
            code=code,
            message=("CRISPR off-target index genome build does not match the requested build."),
        )
    if (
        inspection.max_mismatches_supported is not None
        and payload.max_mismatches > inspection.max_mismatches_supported
    ):
        code = unsupported_input_warning("offtarget_mismatch_radius")
        raise CrisprOffTargetIndexUnsupported(
            code=code,
            message=(
                "Indexed CRISPR off-target screening is configured for "
                f"up to {inspection.max_mismatches_supported} mismatch(es)."
            ),
        )

    with _connect_readonly(Path(index_path)) as conn:
        candidates = _query_candidate_rows(
            conn,
            guide=guide,
            pam_pattern=payload.pam,
            max_mismatches=payload.max_mismatches,
            on_target_locus=payload.on_target_locus,
        )

    if payload.on_target_locus is not None and not any(site.on_target for site in candidates):
        candidates.append(_requested_on_target_site(payload))

    sites = sorted(
        candidates,
        key=lambda site: (
            not site.on_target,
            site.mismatches,
            -site.score,
            site.chromosome,
            site.position,
            site.strand,
        ),
    )[: max(1, max_results)]
    return CrisprOffTargetResponse(genome_build=payload.genome_build, sites=sites)


def _validate_spcas9_payload(payload: CrisprOffTargetRequest) -> None:
    if payload.enzyme != "SpCas9":
        code = unsupported_input_warning("enzyme")
        raise CrisprOffTargetIndexUnsupported(
            code=code,
            message="CRISPR off-target screening currently supports SpCas9 NGG only.",
        )
    if len(payload.pam) != SPCAS9_PAM_LENGTH:
        code = unsupported_input_warning("pam")
        raise CrisprOffTargetIndexUnsupported(
            code=code,
            message="Indexed CRISPR off-target screening currently supports 3 nt SpCas9 PAMs.",
        )
    if payload.max_mismatches > DEFAULT_INDEX_MAX_MISMATCHES_SUPPORTED:
        code = unsupported_input_warning("offtarget_mismatch_radius")
        raise CrisprOffTargetIndexUnsupported(
            code=code,
            message=(
                "Indexed CRISPR off-target screening supports up to "
                f"{DEFAULT_INDEX_MAX_MISMATCHES_SUPPORTED} mismatch(es)."
            ),
        )


def _iter_spcas9_targets(sequence: str) -> Iterator[tuple[str, str, str, int]]:
    template = clean_dna(sequence)
    for spacer_start in range(0, len(template) - SPCAS9_TARGET_LENGTH + 1):
        spacer_end = spacer_start + SPCAS9_SPACER_LENGTH
        pam_end = spacer_end + SPCAS9_PAM_LENGTH
        spacer = template[spacer_start:spacer_end]
        pam = template[spacer_end:pam_end]
        if "N" in spacer or "N" in pam or not is_spcas9_pam(pam):
            continue
        yield spacer, pam, "+", spacer_start + 18

    reverse_template = reverse_complement(template)
    sequence_length = len(template)
    for rc_spacer_start in range(0, sequence_length - SPCAS9_TARGET_LENGTH + 1):
        rc_spacer_end = rc_spacer_start + SPCAS9_SPACER_LENGTH
        rc_pam_end = rc_spacer_end + SPCAS9_PAM_LENGTH
        spacer = reverse_template[rc_spacer_start:rc_spacer_end]
        pam = reverse_template[rc_spacer_end:rc_pam_end]
        if "N" in spacer or "N" in pam or not is_spcas9_pam(pam):
            continue
        pam_start = sequence_length - rc_pam_end
        yield spacer, pam, "-", pam_start + 6


def _query_candidate_rows(
    conn: sqlite3.Connection,
    *,
    guide: str,
    pam_pattern: str,
    max_mismatches: int,
    on_target_locus: CrisprOffTargetLocus | None,
) -> list[CrisprOffTargetSite]:
    sites: list[CrisprOffTargetSite] = []
    seen: set[tuple[str, int, str, str, str]] = set()
    for chunk in _chunked(_spacer_neighbors(guide, max_mismatches), SQLITE_BIND_CHUNK_SIZE):
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            "SELECT spacer, pam, chromosome, strand, position, gene, gene_id, biotype "
            f"FROM targets WHERE spacer IN ({placeholders})",
            chunk,
        ).fetchall()
        for row in rows:
            pam = str(row["pam"])
            if not _pam_matches(pam_pattern, pam):
                continue
            spacer = str(row["spacer"])
            mismatches = len(hsu_mismatch_positions(guide, spacer))
            if mismatches > max_mismatches:
                continue
            chromosome = _normalize_chromosome(str(row["chromosome"]))
            strand = str(row["strand"])
            position = int(row["position"])
            key = (chromosome, position, strand, spacer, pam)
            if key in seen:
                continue
            seen.add(key)
            is_on_target = _is_on_target(
                chromosome=chromosome,
                position=position,
                strand=strand,
                locus=on_target_locus,
            )
            sites.append(
                CrisprOffTargetSite(
                    sequence=spacer,
                    pam=pam,
                    score=round(hsu_off_target_cutting_score(guide, spacer) / 100.0, 6),
                    mismatches=mismatches,
                    gene="ON_TARGET" if is_on_target else row["gene"],
                    gene_id=row["gene_id"],
                    biotype="protein_coding" if is_on_target else row["biotype"],
                    chromosome=chromosome,
                    strand=strand,
                    position=position,
                    on_target=is_on_target,
                )
            )
    return sites


def _requested_on_target_site(payload: CrisprOffTargetRequest) -> CrisprOffTargetSite:
    locus = payload.on_target_locus
    assert locus is not None
    return CrisprOffTargetSite(
        sequence=payload.guide,
        pam=_concrete_pam(payload.pam),
        score=1.0,
        mismatches=0,
        gene="ON_TARGET",
        gene_id=None,
        biotype="protein_coding",
        chromosome=_normalize_chromosome(locus.chromosome),
        strand=locus.strand,
        position=locus.position,
        on_target=True,
    )


def _spacer_neighbors(spacer: str, max_mismatches: int) -> Iterator[str]:
    spacer = clean_dna(spacer)
    yield spacer
    positions = range(len(spacer))
    for distance in range(1, max_mismatches + 1):
        for changed_positions in combinations(positions, distance):
            replacements = [
                tuple(base for base in "ACGT" if base != spacer[position])
                for position in changed_positions
            ]
            for bases in product(*replacements):
                candidate = list(spacer)
                for position, base in zip(changed_positions, bases):
                    candidate[position] = base
                yield "".join(candidate)


def _chunked(items: Iterator[str], chunk_size: int) -> Iterator[list[str]]:
    chunk: list[str] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _pam_matches(pattern: str, pam: str) -> bool:
    pattern = pattern.upper()
    pam = pam.upper()
    return len(pattern) == len(pam) and all(
        expected == "N" or expected == observed for expected, observed in zip(pattern, pam)
    )


def _concrete_pam(pattern: str) -> str:
    return "".join("A" if base == "N" else base for base in pattern.upper())


def _is_on_target(
    *,
    chromosome: str,
    position: int,
    strand: str,
    locus: CrisprOffTargetLocus | None,
) -> bool:
    if locus is None:
        return False
    return (
        chromosome == _normalize_chromosome(locus.chromosome)
        and position == locus.position
        and strand == locus.strand
    )


def _normalize_chromosome(chromosome: str) -> str:
    raw = chromosome.strip()
    if raw.lower().startswith("chr"):
        raw = raw[3:]
    raw = raw.upper()
    if raw == "MT":
        raw = "M"
    return f"chr{raw}"


def _normalize_build(build: str) -> str:
    value = build.strip().lower()
    if value == "hg38":
        return "grch38"
    return value


def _connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE targets (
            id INTEGER PRIMARY KEY,
            spacer TEXT NOT NULL,
            pam TEXT NOT NULL,
            chromosome TEXT NOT NULL,
            strand TEXT NOT NULL,
            position INTEGER NOT NULL,
            gene TEXT,
            gene_id TEXT,
            biotype TEXT
        );
        """)


def _write_metadata(conn: sqlite3.Connection, values: dict[str, str]) -> None:
    conn.executemany(
        "INSERT INTO metadata(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        values.items(),
    )


def _insert_targets(
    conn: sqlite3.Connection,
    rows: list[tuple[str, str, str, str, int, str | None, str | None, str | None]],
) -> None:
    conn.executemany(
        "INSERT INTO targets(spacer, pam, chromosome, strand, position, gene, gene_id, biotype) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def _metadata(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM metadata").fetchall()
    return {str(row["key"]): str(row["value"]) for row in rows}


def _metadata_int(metadata: dict[str, str], key: str) -> int | None:
    value = metadata.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _target_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS count FROM targets").fetchone()
    return int(row["count"]) if row is not None else 0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and query the EAMOS local SpCas9 off-target SQLite index."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    source = build_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fasta", type=Path)
    source.add_argument("--twobit", type=Path)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--genome-build", default="GRCh38")
    build_parser.add_argument("--source-version")
    build_parser.add_argument(
        "--max-mismatches-supported",
        type=int,
        default=DEFAULT_INDEX_MAX_MISMATCHES_SUPPORTED,
    )

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--index", type=Path, required=True)

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--index", type=Path, required=True)
    query_parser.add_argument("--guide", required=True)
    query_parser.add_argument("--pam", default="NGG")
    query_parser.add_argument("--genome-build", default="GRCh38")
    query_parser.add_argument("--max-mismatches", type=int, default=3)
    query_parser.add_argument("--max-results", type=int, default=20)
    return parser


def cli_main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "build":
        records = iter_fasta_records(args.fasta) if args.fasta else iter_twobit_records(args.twobit)
        inspection = build_spcas9_offtarget_index_from_sequences(
            records,
            args.output,
            genome_build=args.genome_build,
            source_version=args.source_version,
            max_mismatches_supported=args.max_mismatches_supported,
        )
        print(json.dumps(inspection.to_sanitized_dict(), sort_keys=True))
        return 0 if inspection.ready else 1
    if args.command == "inspect":
        print(
            json.dumps(
                inspect_crispr_offtarget_index(args.index).to_sanitized_dict(), sort_keys=True
            )
        )
        return 0
    if args.command == "query":
        response = query_spcas9_offtarget_index(
            args.index,
            CrisprOffTargetRequest(
                guide=args.guide,
                pam=args.pam,
                genome_build=args.genome_build,
                max_mismatches=args.max_mismatches,
            ),
            max_results=args.max_results,
        )
        print(response.model_dump_json())
        return 0
    parser.error("unknown command")
    return 2
