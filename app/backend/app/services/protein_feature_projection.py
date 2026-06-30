from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

from app.schemas.gene_viewer import (
    ProteinActiveSite,
    ProteinDomain,
    ProteinFeatures,
    ProteinPointFeature,
    ProteinRangeFeature,
)
from app.schemas.protein_annotation import (
    ProteinDomainTrack,
    ProteinDomainTrackFeature,
    ProteinTrackProvenance,
)

_BUNDLED_FEATURE_SEED_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "protein_feature_seeds.json"
)


@dataclass(frozen=True)
class BundledProteinFeatureSeed:
    features: tuple[ProteinDomainTrackFeature, ...]
    provenance: ProteinTrackProvenance


@lru_cache(maxsize=1)
def _bundled_protein_feature_seeds() -> dict[str, BundledProteinFeatureSeed]:
    if not _BUNDLED_FEATURE_SEED_PATH.is_file():
        return {}
    try:
        raw = json.loads(_BUNDLED_FEATURE_SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}

    seeds: dict[str, BundledProteinFeatureSeed] = {}
    for gene, payload in raw.items():
        if not isinstance(gene, str) or not isinstance(payload, dict):
            continue
        raw_features = payload.get("features")
        if not isinstance(raw_features, list):
            continue
        try:
            features = tuple(
                ProteinDomainTrackFeature.model_validate(feature)
                for feature in raw_features
                if isinstance(feature, dict)
            )
            provenance = ProteinTrackProvenance(
                source_id=str(payload["source_id"]),
                source_name=str(payload["source_name"]),
                source_url=(
                    str(payload["source_url"]) if payload.get("source_url") is not None else None
                ),
                source_release=(
                    str(payload["source_release"])
                    if payload.get("source_release") is not None
                    else None
                ),
                warnings=["bundled_feature_seed"],
            )
        except (KeyError, TypeError, ValueError):
            continue
        if features:
            seeds[gene.strip().upper()] = BundledProteinFeatureSeed(
                features=features,
                provenance=provenance,
            )
    return seeds


def _feature_identity(
    feature: ProteinDomainTrackFeature,
) -> tuple[str, int, int, str]:
    return (
        feature.accession or feature.source_accession or feature.label,
        feature.aa_start,
        feature.aa_end,
        feature.kind,
    )


def _track_with_bundled_feature_seed(track: ProteinDomainTrack) -> ProteinDomainTrack:
    gene = (track.gene_symbol or "").strip().upper()
    if not gene:
        return track
    seed = _bundled_protein_feature_seeds().get(gene)
    if seed is None:
        return track

    existing_keys = {_feature_identity(feature) for feature in track.features}
    protein_length = track.protein_length
    seed_features: list[ProteinDomainTrackFeature] = []
    for feature in seed.features:
        if protein_length is not None and feature.aa_end > protein_length:
            continue
        key = _feature_identity(feature)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        seed_features.append(feature)
    if not seed_features:
        return track

    provenance = list(track.provenance)
    if all(item.source_id != seed.provenance.source_id for item in provenance):
        provenance.append(seed.provenance)
    warning = f"bundled_protein_feature_seed:{gene}"
    status = track.status if track.status in {"available", "cache_hit", "partial"} else "partial"
    return track.model_copy(
        update={
            "status": status,
            "features": [*track.features, *seed_features],
            "provenance": provenance,
            "warnings": _dedupe([*track.warnings, warning]),
        },
        deep=True,
    )


def _feature_text(feature: ProteinDomainTrackFeature) -> str:
    return f"{feature.kind} {feature.label} {feature.short_label or ''} {feature.description or ''}".lower()


def _range_feature_from_track(feature: ProteinDomainTrackFeature) -> ProteinRangeFeature:
    return ProteinRangeFeature(
        aa_start=feature.aa_start,
        aa_end=feature.aa_end,
        label=feature.label,
    )


def _point_feature_residue(feature: ProteinDomainTrackFeature) -> str:
    text = _feature_text(feature)
    if "palmitoyl" in text or "palmitoylation" in text:
        return "C"
    if "iron" in text or "fe" in text:
        return "H"
    return "?"


def _point_feature_from_track(feature: ProteinDomainTrackFeature) -> ProteinPointFeature:
    return ProteinPointFeature(
        aa=feature.aa_start,
        residue=_point_feature_residue(feature),
        label=feature.label,
    )


def _active_site_from_track(feature: ProteinDomainTrackFeature) -> ProteinActiveSite:
    return ProteinActiveSite(
        aa=feature.aa_start,
        residue=_point_feature_residue(feature),
        label=feature.label,
    )


def _append_unique_range_feature(
    items: list[ProteinRangeFeature],
    feature: ProteinRangeFeature,
) -> None:
    key = (feature.aa_start, feature.aa_end, feature.label)
    if key not in {(item.aa_start, item.aa_end, item.label) for item in items}:
        items.append(feature)


def _append_unique_point_feature(
    items: list[ProteinPointFeature],
    feature: ProteinPointFeature,
) -> None:
    key = (feature.aa, feature.residue, feature.label)
    if key not in {(item.aa, item.residue, item.label) for item in items}:
        items.append(feature)


def _append_unique_active_site(
    items: list[ProteinActiveSite],
    feature: ProteinActiveSite,
) -> None:
    key = (feature.aa, feature.residue, feature.label)
    if key not in {(item.aa, item.residue, item.label) for item in items}:
        items.append(feature)


def protein_features_from_domain_track(
    existing: ProteinFeatures,
    track: ProteinDomainTrack,
) -> ProteinFeatures:
    updated = existing.model_copy(deep=True)
    track = _track_with_bundled_feature_seed(track)
    updated.domain_track = track
    if track.status not in {"available", "cache_hit", "partial"}:
        return updated
    existing_keys = {(item.aa_start, item.aa_end, item.label) for item in updated.domains}
    for feature in track.features:
        text = _feature_text(feature)
        if feature.kind == "signal_peptide" and updated.signal_peptide is None:
            updated.signal_peptide = _range_feature_from_track(feature)
        if feature.kind == "transmembrane":
            _append_unique_range_feature(
                updated.transmembrane,
                _range_feature_from_track(feature),
            )
        if feature.kind in {"region", "motif"} and ("membrane" in text or "amphipathic" in text):
            _append_unique_range_feature(
                updated.membrane_binding,
                _range_feature_from_track(feature),
            )
        if feature.kind == "site" and (
            "active" in text or "binding" in text or "iron" in text or "fe" in text
        ):
            _append_unique_active_site(
                updated.active_sites,
                _active_site_from_track(feature),
            )
        if feature.kind == "site" and ("palmitoyl" in text or "palmitoylation" in text):
            _append_unique_point_feature(
                updated.palmitoylation,
                _point_feature_from_track(feature),
            )
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
    updated.active_sites.sort(key=lambda item: (item.aa, item.label))
    updated.membrane_binding.sort(key=lambda item: (item.aa_start, item.aa_end, item.label))
    updated.palmitoylation.sort(key=lambda item: (item.aa, item.label))
    updated.transmembrane.sort(key=lambda item: (item.aa_start, item.aa_end, item.label))
    return updated


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
