from __future__ import annotations

from dataclasses import dataclass


CC0_LICENSES = frozenset({"cc0", "cc0-1.0", "creative commons zero v1.0 universal"})


@dataclass(frozen=True)
class MaveDbRecord:
    score_set_id: str
    variant: str
    score: float | None
    license: str | None
    gene: str | None = None
    accession: str | None = None


@dataclass(frozen=True)
class MaveDbImportResult:
    accepted: tuple[MaveDbRecord, ...]
    rejected: tuple[MaveDbRecord, ...]
    warnings: tuple[str, ...]
    provenance: tuple[str, ...] = ("eamos_mavedb_cc0_gate_v1",)


def filter_mavedb_cc0_records(records: list[MaveDbRecord]) -> MaveDbImportResult:
    accepted: list[MaveDbRecord] = []
    rejected: list[MaveDbRecord] = []
    warnings: list[str] = []
    for record in records:
        license_key = (record.license or "").strip().lower()
        if license_key not in CC0_LICENSES:
            rejected.append(record)
            warnings.append(f"mavedb_non_cc0_rejected:{record.score_set_id}")
            continue
        if record.score is None:
            rejected.append(record)
            warnings.append(f"mavedb_missing_score_rejected:{record.score_set_id}")
            continue
        accepted.append(record)
    return MaveDbImportResult(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        warnings=tuple(warnings),
    )
