from __future__ import annotations

import json
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from app.schemas.workbench import CrisprGuide, CrisprRequest, CrisprResponse
from app.services.sequence_context import SequenceContext, unsupported_input_warning

CRISPR_PROVIDER_CRISPRSCORE_R = "crisprscore_r"
CRISPR_PROVIDER_LOCAL_DETERMINISTIC = "local_deterministic"
SPCAS9_SPACER_LENGTH = 20
SPCAS9_PAM_LENGTH = 3
SPCAS9_TARGET_LENGTH = SPCAS9_SPACER_LENGTH + SPCAS9_PAM_LENGTH
HSU_DISTANCE_PENALTY_CONSTANT = 4.0
MAX_RETURNED_GUIDES = 6
CRISPR_MAX_SEQUENCE_BASES = 20_000
CRISPRSCORE_R_TIMEOUT_SECONDS = 30.0

# MIT/Hsu 2013 position penalties, indexed from PAM-distal to PAM-proximal.
HSU_MISMATCH_PENALTIES: tuple[float, ...] = (
    0.000,
    0.000,
    0.014,
    0.000,
    0.000,
    0.395,
    0.317,
    0.000,
    0.389,
    0.079,
    0.445,
    0.508,
    0.613,
    0.851,
    0.732,
    0.828,
    0.615,
    0.804,
    0.685,
    0.583,
)

Strand = Literal["+", "-"]


class CrisprDesignInputError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.warnings = warnings if warnings is not None else [code]


@dataclass(frozen=True)
class SpCas9PamSite:
    spacer: str
    pam: str
    strand: Strand
    spacer_start: int
    spacer_end: int
    pam_start: int
    pam_end: int
    cut_position: int
    deep_hf_context: str


@dataclass(frozen=True)
class HsuOffTarget:
    site: SpCas9PamSite
    mismatches: tuple[int, ...]
    cutting_score: float


@dataclass(frozen=True)
class CrisprScoreCandidate:
    id: str
    site: SpCas9PamSite
    off_targets: tuple[HsuOffTarget, ...]
    ruleset_context: str | None
    crisprscan_context: str | None
    lindel_context: str | None


@dataclass(frozen=True)
class CrisprSourceScores:
    ruleset1: float | None = None
    ruleset3: float | None = None
    crisprscan: float | None = None
    crisprater: float | None = None
    mit_specificity: float | None = None
    cfd_specificity: float | None = None
    lindel_frameshift: float | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CrisprScoreRuntimeInspection:
    configured_provider: str
    available: bool
    status: str
    checks: dict[str, bool | None]
    score_families: dict[str, dict[str, object]]
    source_id: str = "eamos_crisprscore_r_runtime"

    def to_sanitized_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "available": self.available,
            "status": self.status,
            "configured_provider": self.configured_provider,
            "checks": self.checks,
            "score_families": self.score_families,
            "platform_gated_models": ["DeepHF", "DeepCpf1", "enPAM+GB"],
            "request_time_install_allowed": False,
            "startup_download_allowed": False,
            "local_path_values_emitted": False,
        }


class CrisprSourceScoringAdapter(Protocol):
    def score(
        self, candidates: tuple[CrisprScoreCandidate, ...]
    ) -> dict[str, CrisprSourceScores]: ...


class CrisprScoreProviderUnavailable(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CrisprScoreProviderError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


_COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def clean_dna(sequence: str) -> str:
    return "".join(base if base in "ACGTN" else "N" for base in sequence.upper())


def reverse_complement(sequence: str) -> str:
    return clean_dna(sequence).translate(_COMPLEMENT)[::-1]


def is_spcas9_pam(pam: str) -> bool:
    pam = clean_dna(pam)
    return len(pam) == SPCAS9_PAM_LENGTH and pam[0] in "ACGT" and pam[1:] == "GG"


def discover_spcas9_pam_sites(
    sequence: str,
    *,
    strand_filter: Literal["both", "plus", "minus"] = "both",
) -> tuple[SpCas9PamSite, ...]:
    template = clean_dna(sequence)
    sites: list[SpCas9PamSite] = []
    if strand_filter in {"both", "plus"}:
        sites.extend(_plus_spcas9_sites(template))
    if strand_filter in {"both", "minus"}:
        sites.extend(_minus_spcas9_sites(template))
    return tuple(
        sorted(sites, key=lambda site: (site.cut_position, site.strand, site.spacer_start))
    )


def _plus_spcas9_sites(sequence: str) -> tuple[SpCas9PamSite, ...]:
    sites: list[SpCas9PamSite] = []
    for spacer_start in range(0, len(sequence) - SPCAS9_TARGET_LENGTH + 1):
        spacer_end = spacer_start + SPCAS9_SPACER_LENGTH
        pam_end = spacer_end + SPCAS9_PAM_LENGTH
        spacer = sequence[spacer_start:spacer_end]
        pam = sequence[spacer_end:pam_end]
        if "N" in spacer or "N" in pam or not is_spcas9_pam(pam):
            continue
        sites.append(
            SpCas9PamSite(
                spacer=spacer,
                pam=pam,
                strand="+",
                spacer_start=spacer_start,
                spacer_end=spacer_end,
                pam_start=spacer_end,
                pam_end=pam_end,
                cut_position=spacer_start + 17,
                deep_hf_context=spacer + pam[0],
            )
        )
    return tuple(sites)


def _minus_spcas9_sites(sequence: str) -> tuple[SpCas9PamSite, ...]:
    reverse_template = reverse_complement(sequence)
    sites: list[SpCas9PamSite] = []
    sequence_length = len(sequence)
    for rc_spacer_start in range(0, sequence_length - SPCAS9_TARGET_LENGTH + 1):
        rc_spacer_end = rc_spacer_start + SPCAS9_SPACER_LENGTH
        rc_pam_end = rc_spacer_end + SPCAS9_PAM_LENGTH
        spacer = reverse_template[rc_spacer_start:rc_spacer_end]
        pam = reverse_template[rc_spacer_end:rc_pam_end]
        if "N" in spacer or "N" in pam or not is_spcas9_pam(pam):
            continue
        pam_start = sequence_length - rc_pam_end
        pam_end = sequence_length - rc_spacer_end
        spacer_start = sequence_length - rc_spacer_end
        spacer_end = sequence_length - rc_spacer_start
        sites.append(
            SpCas9PamSite(
                spacer=spacer,
                pam=pam,
                strand="-",
                spacer_start=spacer_start,
                spacer_end=spacer_end,
                pam_start=pam_start,
                pam_end=pam_end,
                cut_position=pam_start + 5,
                deep_hf_context=spacer + pam[0],
            )
        )
    return tuple(sites)


def hsu_mismatch_positions(spacer: str, protospacer: str) -> tuple[int, ...]:
    spacer = clean_dna(spacer)
    protospacer = clean_dna(protospacer)
    if len(spacer) != SPCAS9_SPACER_LENGTH or len(protospacer) != SPCAS9_SPACER_LENGTH:
        raise ValueError("Hsu scoring requires 20 nt spacer and protospacer sequences.")
    return tuple(
        idx
        for idx, (spacer_base, protospacer_base) in enumerate(zip(spacer, protospacer))
        if spacer_base != protospacer_base
    )


def hsu_off_target_cutting_score(spacer: str, protospacer: str) -> float:
    mismatches = hsu_mismatch_positions(spacer, protospacer)
    if not mismatches:
        return 100.0

    position_factor = 1.0
    for position in mismatches:
        position_factor *= 1.0 - HSU_MISMATCH_PENALTIES[position]

    distance_factor = 1.0
    if len(mismatches) > 1:
        distances = [later - earlier for earlier, later in zip(mismatches, mismatches[1:])]
        average_distance = sum(distances) / len(distances)
        distance_factor = 1.0 / (
            (((SPCAS9_SPACER_LENGTH - 1) - average_distance) / (SPCAS9_SPACER_LENGTH - 1))
            * HSU_DISTANCE_PENALTY_CONSTANT
            + 1.0
        )

    mismatch_count_factor = 1.0 / (len(mismatches) ** 2)
    score = 100.0 * position_factor * distance_factor * mismatch_count_factor
    return round(max(0.0, min(100.0, score)), 6)


def hsu_specificity_score(off_target_cutting_scores: list[float]) -> float:
    if not off_target_cutting_scores:
        return 100.0
    return round(10000.0 / (100.0 + sum(off_target_cutting_scores)), 6)


def inspect_crisprscore_r_runtime(
    *,
    configured_provider: str = CRISPR_PROVIDER_LOCAL_DETERMINISTIC,
    rscript_path: str | Path = "Rscript",
    rule_set3_conda_env: str | Path | None = None,
    lindel_conda_env: str | Path | None = None,
    runner: Any = subprocess.run,
    package_timeout_seconds: float = 5.0,
) -> CrisprScoreRuntimeInspection:
    provider = (configured_provider or "").strip().lower() or CRISPR_PROVIDER_LOCAL_DETERMINISTIC
    checks: dict[str, bool | None] = {
        "rscript": False,
        "jsonlite_package": None,
        "crisprscore_package": None,
        "rule_set3_conda_env_configured": rule_set3_conda_env is not None,
        "lindel_conda_env_configured": lindel_conda_env is not None,
    }
    if provider != CRISPR_PROVIDER_CRISPRSCORE_R:
        return CrisprScoreRuntimeInspection(
            configured_provider=provider,
            available=False,
            status="disabled",
            checks=checks,
            score_families=_crisprscore_score_families(checks),
        )

    rscript = _resolve_executable(rscript_path)
    if rscript is None:
        return CrisprScoreRuntimeInspection(
            configured_provider=provider,
            available=False,
            status="unavailable",
            checks=checks,
            score_families=_crisprscore_score_families(checks),
        )

    checks["rscript"] = True
    checks.update(
        probe_crisprscore_r_packages(
            rscript,
            runner=runner,
            timeout_seconds=package_timeout_seconds,
        )
    )
    available = bool(checks["jsonlite_package"] and checks["crisprscore_package"])
    return CrisprScoreRuntimeInspection(
        configured_provider=provider,
        available=available,
        status="available" if available else "unavailable",
        checks=checks,
        score_families=_crisprscore_score_families(checks),
    )


def probe_crisprscore_r_packages(
    rscript: str,
    *,
    runner: Any = subprocess.run,
    timeout_seconds: float = 5.0,
) -> dict[str, bool | None]:
    script = (
        "cat('{\"jsonlite_package\":'); "
        "cat(if (requireNamespace('jsonlite', quietly=TRUE)) 'true' else 'false'); "
        "cat(',\"crisprscore_package\":'); "
        "cat(if (requireNamespace('crisprScore', quietly=TRUE)) 'true' else 'false'); "
        "cat('}')"
    )
    try:
        completed = runner(
            [rscript, "--vanilla", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"jsonlite_package": None, "crisprscore_package": None}

    if completed.returncode != 0:
        return {"jsonlite_package": None, "crisprscore_package": None}
    try:
        decoded = json.loads(completed.stdout or "{}")
    except ValueError:
        return {"jsonlite_package": None, "crisprscore_package": None}
    return {
        "jsonlite_package": (
            decoded["jsonlite_package"]
            if isinstance(decoded.get("jsonlite_package"), bool)
            else None
        ),
        "crisprscore_package": (
            decoded["crisprscore_package"]
            if isinstance(decoded.get("crisprscore_package"), bool)
            else None
        ),
    }


def _resolve_executable(path: str | Path) -> str | None:
    raw_path = str(path)
    resolved = shutil.which(raw_path)
    if resolved:
        return resolved
    candidate = Path(raw_path)
    if candidate.is_file():
        return str(candidate)
    return None


def _crisprscore_score_families(
    checks: dict[str, bool | None],
) -> dict[str, dict[str, object]]:
    package_ready = bool(checks["jsonlite_package"] and checks["crisprscore_package"])
    rule_set3_ready = bool(package_ready and checks["rule_set3_conda_env_configured"])
    lindel_ready = bool(package_ready and checks["lindel_conda_env_configured"])
    rule_set3_status = (
        "available"
        if rule_set3_ready
        else "unavailable" if not package_ready else "conda_env_required"
    )
    lindel_status = (
        "available"
        if lindel_ready
        else "unavailable" if not package_ready else "conda_env_required"
    )
    return {
        "ruleset1": {
            "available": package_ready,
            "status": "available" if package_ready else "unavailable",
            "runtime": "crisprScore",
        },
        "ruleset3": {
            "available": rule_set3_ready,
            "status": rule_set3_status,
            "runtime": "crisprScore_rule_set3",
        },
        "crisprscan": {
            "available": package_ready,
            "status": "available" if package_ready else "unavailable",
            "runtime": "crisprScore",
        },
        "crisprater": {
            "available": package_ready,
            "status": "available" if package_ready else "unavailable",
            "runtime": "crisprScore",
        },
        "mit_specificity": {
            "available": package_ready,
            "status": "available" if package_ready else "unavailable",
            "runtime": "crisprScore",
        },
        "cfd_specificity": {
            "available": package_ready,
            "status": "available" if package_ready else "unavailable",
            "runtime": "crisprScore",
        },
        "lindel_frameshift": {
            "available": lindel_ready,
            "status": lindel_status,
            "runtime": "crisprScore_lindel",
        },
    }


class CrisprScoreRAdapter:
    """Windows-safe Rscript boundary for Bioconductor crisprScore."""

    def __init__(
        self,
        *,
        rscript_path: str | Path = "Rscript",
        timeout_seconds: float = CRISPRSCORE_R_TIMEOUT_SECONDS,
        rule_set3_conda_env: str | Path | None = None,
        lindel_conda_env: str | Path | None = None,
        runner: Any = subprocess.run,
    ) -> None:
        self.rscript_path = rscript_path
        self.timeout_seconds = timeout_seconds
        self.rule_set3_conda_env = str(rule_set3_conda_env) if rule_set3_conda_env else None
        self.lindel_conda_env = str(lindel_conda_env) if lindel_conda_env else None
        self.runner = runner

    def score(self, candidates: tuple[CrisprScoreCandidate, ...]) -> dict[str, CrisprSourceScores]:
        if not candidates:
            return {}

        rscript = self._resolve_rscript()
        payload = {
            "rows": [_crisprscore_candidate_payload(candidate) for candidate in candidates],
            "rule_set3_conda_env": self.rule_set3_conda_env,
            "lindel_conda_env": self.lindel_conda_env,
        }
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".R",
            encoding="utf-8",
            delete=False,
        ) as script_file:
            script_file.write(_CRISPRSCORE_R_SCRIPT)
            script_path = Path(script_file.name)

        try:
            completed = self.runner(
                [rscript, "--vanilla", str(script_path)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CrisprScoreProviderError("crisprScore Rscript scoring timed out.") from exc
        except OSError as exc:
            raise CrisprScoreProviderUnavailable(
                "Rscript executable could not be launched."
            ) from exc
        finally:
            try:
                script_path.unlink()
            except OSError:
                pass

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            if "there is no package called" in stderr or "crisprScore" in stderr:
                raise CrisprScoreProviderUnavailable(
                    "crisprScore Rscript dependencies are unavailable."
                )
            raise CrisprScoreProviderError("crisprScore Rscript scoring failed.")

        try:
            decoded = json.loads(completed.stdout or "{}")
        except ValueError as exc:
            raise CrisprScoreProviderError("crisprScore Rscript returned malformed JSON.") from exc
        return _parse_crisprscore_response(decoded)

    def _resolve_rscript(self) -> str:
        resolved = _resolve_executable(self.rscript_path)
        if resolved is not None:
            return resolved
        raise CrisprScoreProviderUnavailable(
            "Rscript executable was not found on PATH or at the configured path."
        )


class CrisprScoreRBackedCrisprProvider:
    def __init__(
        self,
        *,
        scoring_adapter: CrisprSourceScoringAdapter | None = None,
        fallback_provider: "LocalDeterministicCrisprProvider" | None = None,
    ) -> None:
        self.fallback_provider = fallback_provider or LocalDeterministicCrisprProvider(
            scoring_adapter=scoring_adapter or CrisprScoreRAdapter(),
        )

    def design(self, payload: CrisprRequest, context: SequenceContext) -> CrisprResponse:
        return self.fallback_provider.design(payload, context)


class LocalDeterministicCrisprProvider:
    def __init__(self, scoring_adapter: CrisprSourceScoringAdapter | None = None) -> None:
        self.scoring_adapter = scoring_adapter

    def design(self, payload: CrisprRequest, context: SequenceContext) -> CrisprResponse:
        if payload.cas != "SpCas9":
            code = unsupported_input_warning("cas")
            raise CrisprDesignInputError(
                code=code,
                message="Real-mode CRISPR design currently supports SpCas9 only.",
                warnings=[code],
            )

        sequence = clean_dna(context.window_sequence)
        if len(sequence) > CRISPR_MAX_SEQUENCE_BASES:
            code = unsupported_input_warning("crispr_sequence_length")
            raise CrisprDesignInputError(
                code=code,
                message=(
                    "CRISPR guide discovery exceeds the bounded local search envelope "
                    f"({CRISPR_MAX_SEQUENCE_BASES} bases)."
                ),
                warnings=[code],
            )
        if len(sequence) < SPCAS9_TARGET_LENGTH:
            code = unsupported_input_warning("sequence_too_short")
            raise CrisprDesignInputError(
                code=code,
                message="Sequence context is too short for SpCas9 NGG guide design.",
                warnings=[code],
            )

        selected_sites = discover_spcas9_pam_sites(
            sequence,
            strand_filter=payload.strand_filter,
        )
        all_sites = discover_spcas9_pam_sites(sequence, strand_filter="both")
        if not selected_sites:
            return CrisprResponse(cas=payload.cas, guides=[], ssodn=None)

        candidate_rows = [
            self._guide_row(
                site=site,
                all_sites=all_sites,
                payload=payload,
                context=context,
            )
            for site in selected_sites
        ]
        ranked = sorted(
            candidate_rows,
            key=lambda row: row["rank"],
        )[:MAX_RETURNED_GUIDES]
        source_scores: dict[str, CrisprSourceScores] = {}
        source_warning: str | None = None
        if self.scoring_adapter is not None:
            candidates = tuple(
                _crisprscore_candidate(
                    candidate_id=str(index),
                    site=row["site"],
                    sequence=sequence,
                    off_targets=tuple(row["off_targets"]),
                )
                for index, row in enumerate(ranked)
            )
            try:
                source_scores = self.scoring_adapter.score(candidates)
            except (CrisprScoreProviderUnavailable, CrisprScoreProviderError) as exc:
                source_warning = exc.message

        guides = []
        for index, row in enumerate(ranked, start=1):
            guide = row["guide"]
            score_id = str(index - 1)
            if score_id in source_scores:
                guide = _guide_with_source_scores(guide, source_scores[score_id])
            elif source_warning is not None:
                guide = _guide_with_appended_note(
                    guide,
                    (
                        f"crisprScore R/Rscript provider unavailable: {source_warning} "
                        "Using local deterministic fallback. "
                        f"{_local_score_provider_labels()}"
                    ),
                )
            guides.append(guide.model_copy(update={"index": index}))

        return CrisprResponse(
            cas=payload.cas,
            guides=guides,
            # Donor design is a separate capability. The legacy response shape
            # requires a numeric HDR-efficiency claim, so no donor is emitted
            # until that field can represent a typed not-assessed state.
            ssodn=None,
        )

    def _guide_row(
        self,
        *,
        site: SpCas9PamSite,
        all_sites: tuple[SpCas9PamSite, ...],
        payload: CrisprRequest,
        context: SequenceContext,
    ) -> dict[str, object]:
        off_targets = _local_off_targets(
            site=site,
            all_sites=all_sites,
            mismatch_tolerance=max(0, payload.off_target_tolerance),
        )
        specificity = hsu_specificity_score(
            [off_target.cutting_score for off_target in off_targets]
        )
        on_target = heuristic_on_target_score(site.spacer)
        cut_distance = abs(site.cut_position - context.target_offset)
        guide = CrisprGuide(
            index=0,
            cut_position=site.cut_position,
            strand=site.strand,
            guide=site.spacer,
            pam=site.pam,
            on_target_score=round(on_target, 1),
            off_target_score=round(100.0 - specificity, 1),
            gc_percent=round(gc_percent(site.spacer), 1),
            notes=_guide_notes(
                site=site,
                context=context,
                off_target_count=len(off_targets),
                mismatch_tolerance=max(0, payload.off_target_tolerance),
                hsu_specificity=specificity,
            ),
        )
        return {
            "guide": guide,
            "site": site,
            "off_targets": tuple(off_targets),
            "rank": (
                cut_distance,
                guide.off_target_score,
                -guide.on_target_score,
                0 if guide.strand == "+" else 1,
                guide.cut_position,
            ),
        }


def _local_off_targets(
    *,
    site: SpCas9PamSite,
    all_sites: tuple[SpCas9PamSite, ...],
    mismatch_tolerance: int,
) -> list[HsuOffTarget]:
    off_targets: list[HsuOffTarget] = []
    for candidate in all_sites:
        if (
            candidate.strand == site.strand
            and candidate.spacer_start == site.spacer_start
            and candidate.pam_start == site.pam_start
        ):
            continue
        mismatches = hsu_mismatch_positions(site.spacer, candidate.spacer)
        if len(mismatches) <= mismatch_tolerance:
            off_targets.append(
                HsuOffTarget(
                    site=candidate,
                    mismatches=mismatches,
                    cutting_score=hsu_off_target_cutting_score(site.spacer, candidate.spacer),
                )
            )
    return off_targets


def _crisprscore_candidate(
    *,
    candidate_id: str,
    site: SpCas9PamSite,
    sequence: str,
    off_targets: tuple[HsuOffTarget, ...],
) -> CrisprScoreCandidate:
    return CrisprScoreCandidate(
        id=candidate_id,
        site=site,
        off_targets=off_targets,
        ruleset_context=_oriented_spcas9_context(
            sequence,
            site=site,
            flank5_length=4,
            flank3_length=3,
        ),
        crisprscan_context=_oriented_spcas9_context(
            sequence,
            site=site,
            flank5_length=6,
            flank3_length=6,
        ),
        lindel_context=_oriented_spcas9_context(
            sequence,
            site=site,
            flank5_length=13,
            flank3_length=29,
        ),
    )


def _oriented_spcas9_context(
    sequence: str,
    *,
    site: SpCas9PamSite,
    flank5_length: int,
    flank3_length: int,
) -> str | None:
    if site.strand == "+":
        start = site.spacer_start - flank5_length
        end = site.pam_end + flank3_length
        if start < 0 or end > len(sequence):
            return None
        return sequence[start:end]

    start = site.pam_start - flank3_length
    end = site.spacer_end + flank5_length
    if start < 0 or end > len(sequence):
        return None
    return reverse_complement(sequence[start:end])


def _crisprscore_candidate_payload(candidate: CrisprScoreCandidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "spacer": candidate.site.spacer,
        "pam": candidate.site.pam,
        "ruleset_context": candidate.ruleset_context,
        "crisprscan_context": candidate.crisprscan_context,
        "lindel_context": candidate.lindel_context,
        "off_targets": [
            {
                "protospacer": off_target.site.spacer,
                "pam": off_target.site.pam,
            }
            for off_target in candidate.off_targets
        ],
    }


def _parse_crisprscore_response(decoded: Any) -> dict[str, CrisprSourceScores]:
    if not isinstance(decoded, dict) or not isinstance(decoded.get("scores"), list):
        raise CrisprScoreProviderError("crisprScore Rscript response is missing score rows.")

    global_warnings = tuple(
        str(warning)
        for warning in decoded.get("warnings", [])
        if isinstance(warning, str) and warning
    )
    parsed: dict[str, CrisprSourceScores] = {}
    for row in decoded["scores"]:
        if not isinstance(row, dict) or "id" not in row:
            raise CrisprScoreProviderError("crisprScore Rscript returned an invalid score row.")
        row_warnings = tuple(
            str(warning)
            for warning in row.get("warnings", [])
            if isinstance(warning, str) and warning
        )
        parsed[str(row["id"])] = CrisprSourceScores(
            ruleset1=_normalized_probability(row.get("ruleset1")),
            ruleset3=_normalized_probability(row.get("ruleset3")),
            crisprscan=_normalized_probability(row.get("crisprscan")),
            crisprater=_normalized_probability(row.get("crisprater")),
            mit_specificity=_normalized_probability(row.get("mit_specificity")),
            cfd_specificity=_normalized_probability(row.get("cfd_specificity")),
            lindel_frameshift=_normalized_probability(row.get("lindel_frameshift")),
            warnings=global_warnings + row_warnings,
        )
    return parsed


def _normalized_probability(value: Any) -> float | None:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score):
        return None
    if 1.0 < score <= 100.0:
        score /= 100.0
    return max(0.0, min(1.0, score))


def _guide_with_source_scores(guide: CrisprGuide, scores: CrisprSourceScores) -> CrisprGuide:
    updates: dict[str, float | str] = {}
    primary_on_target = _primary_on_target_score(scores)
    if primary_on_target is not None:
        _label, score = primary_on_target
        updates["on_target_score"] = round(score * 100.0, 1)

    primary_specificity = _primary_off_target_specificity(scores)
    if primary_specificity is not None:
        _label, specificity = primary_specificity
        updates["off_target_score"] = round(100.0 - (specificity * 100.0), 1)

    updates["notes"] = _append_note_text(guide.notes, _source_score_note(scores))
    return guide.model_copy(update=updates)


def _primary_on_target_score(scores: CrisprSourceScores) -> tuple[str, float] | None:
    for label, score in (
        ("RuleSet3", scores.ruleset3),
        ("RuleSet1", scores.ruleset1),
        ("CRISPRscan", scores.crisprscan),
        ("CRISPRater", scores.crisprater),
    ):
        if score is not None:
            return label, score
    return None


def _primary_off_target_specificity(scores: CrisprSourceScores) -> tuple[str, float] | None:
    for label, score in (("CFD", scores.cfd_specificity), ("MIT", scores.mit_specificity)):
        if score is not None:
            return label, score
    return None


def _guide_with_appended_note(guide: CrisprGuide, note: str) -> CrisprGuide:
    return guide.model_copy(update={"notes": _append_note_text(guide.notes, note)})


def _append_note_text(existing: str, note: str) -> str:
    return f"{existing.rstrip()} {note}".strip()


def _source_score_note(scores: CrisprSourceScores) -> str:
    primary_on_target = _primary_on_target_score(scores)
    primary_specificity = _primary_off_target_specificity(scores)
    primary_on_target_label = primary_on_target[0] if primary_on_target is not None else "fallback"
    primary_specificity_label = (
        primary_specificity[0] if primary_specificity is not None else "fallback"
    )
    note = (
        "crisprScore R/Rscript source scores. "
        "Provider labels: on-target "
        f"RuleSet1={_format_probability(scores.ruleset1)}, "
        f"RuleSet3={_format_probability(scores.ruleset3)}, "
        f"CRISPRscan={_format_probability(scores.crisprscan)}, "
        f"CRISPRater={_format_probability(scores.crisprater)}; "
        "MIT/CFD off-target "
        f"MIT={_format_specificity(scores.mit_specificity)}, "
        f"CFD={_format_specificity(scores.cfd_specificity)}; "
        f"Lindel frameshift={_format_probability(scores.lindel_frameshift)}; "
        "DeepHF/DeepCpf1/enPAM+GB=platform-gated Windows-unavailable. "
        f"Primary on-target provider: {primary_on_target_label}; "
        f"primary off-target provider: {primary_specificity_label}."
    )
    if scores.warnings:
        note = f"{note} crisprScore warnings: {'; '.join(scores.warnings[:3])}."
    return note


def _local_score_provider_labels() -> str:
    return (
        "Provider labels: on-target RuleSet1=unavailable, RuleSet3=unavailable, "
        "CRISPRscan=unavailable, CRISPRater=unavailable; MIT/CFD off-target "
        "MIT=local Hsu/MIT in-context, CFD=unavailable; Lindel frameshift=unavailable; "
        "DeepHF/DeepCpf1/enPAM+GB=platform-gated Windows-unavailable."
    )


def _format_probability(score: float | None) -> str:
    return "unavailable" if score is None else f"{score * 100.0:.1f}"


def _format_specificity(score: float | None) -> str:
    return "unavailable" if score is None else f"{score * 100.0:.1f} specificity"


_CRISPRSCORE_R_SCRIPT = r"""
fail <- function(message) {
  cat(jsonlite::toJSON(list(error=message), auto_unbox=TRUE))
  quit(status=1)
}

if (!requireNamespace("jsonlite", quietly=TRUE)) {
  stop("The jsonlite R package is required for crisprScore adapter JSON IO.")
}
if (!requireNamespace("crisprScore", quietly=TRUE)) {
  stop("The Bioconductor crisprScore package is not installed.")
}

payload <- jsonlite::fromJSON(file("stdin"), simplifyVector=FALSE)
rows <- payload$rows
warnings <- c()

empty_to_null <- function(value) {
  if (is.null(value) || length(value) == 0 || is.na(value) || identical(value, "")) {
    return(NULL)
  }
  value
}

extract_scores <- function(result) {
  if (is.data.frame(result) && "score" %in% names(result)) {
    return(as.numeric(result$score))
  }
  as.numeric(result)
}

write_method_scores <- function(method_name, inputs, scorer) {
  output <- rep(NA_real_, length(inputs))
  valid <- which(!is.na(inputs) & nzchar(inputs))
  if (length(valid) == 0) {
    return(output)
  }
  result <- tryCatch(
    extract_scores(scorer(inputs[valid])),
    error=function(e) {
      warnings <<- c(warnings, paste0(method_name, " unavailable: ", conditionMessage(e)))
      return(NULL)
    }
  )
  if (!is.null(result)) {
    output[valid] <- result
  }
  output
}

specificity_from_risk <- function(scores) {
  scores <- scores[!is.na(scores)]
  if (length(scores) == 0) {
    return(1.0)
  }
  100.0 / (100.0 + sum(scores * 100.0))
}

score_off_targets <- function(row, method_name, scorer) {
  off_targets <- row$off_targets
  if (length(off_targets) == 0) {
    return(1.0)
  }
  protospacers <- vapply(off_targets, function(x) x$protospacer, character(1))
  pams <- vapply(off_targets, function(x) x$pam, character(1))
  spacers <- rep(row$spacer, length(protospacers))
  result <- tryCatch(
    extract_scores(scorer(spacers=spacers, protospacers=protospacers, pams=pams)),
    error=function(e) {
      warnings <<- c(warnings, paste0(method_name, " unavailable: ", conditionMessage(e)))
      return(NULL)
    }
  )
  if (is.null(result)) {
    return(NA_real_)
  }
  specificity_from_risk(result)
}

ids <- vapply(rows, function(row) row$id, character(1))
spacers <- vapply(rows, function(row) row$spacer, character(1))
ruleset_contexts <- vapply(
  rows,
  function(row) if (is.null(row$ruleset_context)) NA_character_ else row$ruleset_context,
  character(1)
)
crisprscan_contexts <- vapply(
  rows,
  function(row) if (is.null(row$crisprscan_context)) NA_character_ else row$crisprscan_context,
  character(1)
)
lindel_contexts <- vapply(
  rows,
  function(row) if (is.null(row$lindel_context)) NA_character_ else row$lindel_context,
  character(1)
)

ruleset1 <- write_method_scores(
  "RuleSet1",
  ruleset_contexts,
  crisprScore::getRuleSet1Scores
)
crisprscan <- write_method_scores(
  "CRISPRscan",
  crisprscan_contexts,
  crisprScore::getCRISPRscanScores
)
crisprater <- write_method_scores(
  "CRISPRater",
  spacers,
  crisprScore::getCRISPRaterScores
)

ruleset3 <- rep(NA_real_, length(rows))
rule_set3_conda_env <- empty_to_null(payload$rule_set3_conda_env)
if (!is.null(rule_set3_conda_env)) {
  ruleset3 <- write_method_scores(
    "RuleSet3",
    ruleset_contexts,
    function(input) crisprScore::getRuleSet3Scores(
      input,
      tracrRNA="Hsu2013",
      condaEnv=rule_set3_conda_env
    )
  )
} else {
  warnings <- c(warnings, "RuleSet3 unavailable: conda environment is not configured")
}

lindel <- rep(NA_real_, length(rows))
lindel_conda_env <- empty_to_null(payload$lindel_conda_env)
if (!is.null(lindel_conda_env)) {
  lindel <- write_method_scores(
    "Lindel",
    lindel_contexts,
    function(input) crisprScore::getLindelScores(input, condaEnv=lindel_conda_env)
  )
} else {
  warnings <- c(warnings, "Lindel frameshift unavailable: conda environment is not configured")
}

mit <- vapply(
  rows,
  function(row) score_off_targets(row, "MIT", crisprScore::getMITScores),
  numeric(1)
)
cfd <- vapply(
  rows,
  function(row) score_off_targets(row, "CFD", crisprScore::getCFDScores),
  numeric(1)
)

score_rows <- lapply(seq_along(rows), function(index) {
  list(
    id=ids[[index]],
    ruleset1=ruleset1[[index]],
    ruleset3=ruleset3[[index]],
    crisprscan=crisprscan[[index]],
    crisprater=crisprater[[index]],
    mit_specificity=mit[[index]],
    cfd_specificity=cfd[[index]],
    lindel_frameshift=lindel[[index]]
  )
})

cat(jsonlite::toJSON(
  list(scores=score_rows, warnings=unique(warnings)),
  auto_unbox=TRUE,
  na="null"
))
"""


def gc_percent(sequence: str) -> float:
    sequence = clean_dna(sequence)
    if not sequence:
        return 0.0
    return 100.0 * sum(1 for base in sequence if base in {"G", "C"}) / len(sequence)


def heuristic_on_target_score(spacer: str) -> float:
    spacer = clean_dna(spacer)
    gc = gc_percent(spacer)
    score = 62.0
    score += max(0.0, 20.0 - abs(gc - 50.0))
    if "TTTT" in spacer:
        score -= 18.0
    if spacer[-1:] in {"G", "C"}:
        score += 4.0
    if spacer[:1] == "G":
        score += 2.0
    return max(0.0, min(100.0, score))


def _guide_notes(
    *,
    site: SpCas9PamSite,
    context: SequenceContext,
    off_target_count: int,
    mismatch_tolerance: int,
    hsu_specificity: float,
) -> str:
    target = context.genomic_hg38 or context.transcript_hgvs
    return (
        "Local deterministic SpCas9 NGG design. "
        f"{_local_score_provider_labels()} "
        "On-target score is a transparent GC/poly-T/PAM-proximal heuristic, not DeepHF. "
        f"In-context Hsu/MIT specificity scan found {off_target_count} candidate(s) "
        f"within {mismatch_tolerance} mismatch(es); Hsu specificity {hsu_specificity:.1f}/100. "
        f"Cut offset {site.cut_position}; template {context.genome_build} {target}. "
        "This is not a genome-wide Bowtie/BWA off-target screen."
    )
