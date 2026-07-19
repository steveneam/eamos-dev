from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any, Literal
import xml.etree.ElementTree as ET

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from app.data_sources import ProductTier, SourceFieldPolicy
from app.schemas.run import (
    LOVD_BASIC_RECORD_FIELD,
    LOVD_FIXTURE_SOURCE_ID,
    LOVD_INSTALLATION_ID,
    LOVD_POLICY_DECIDED_AT,
    LovdBasicObservation,
    LovdBasicRecordsSection,
    LovdInstallationSource,
    SourcePolicyDecision,
)

_ATOM_NS = "http://www.w3.org/2005/Atom"
_LOVD_FIXTURE_NS = "urn:eamos:fixture:lovd-basic:v1"
_FIXTURE_STATUS = "hand_authored_synthetic"
_ALLOWED_RECORD_LICENSE = "CC-BY-4.0"
_MAX_FIXTURE_BYTES = 65_536
_MAX_FIXTURE_RECORDS = 100
_VERSIONED_TRANSCRIPT_RE = re.compile(r"(?:NM|NR)_\d+\.\d+")
_CDNA_RE = re.compile(r"c\.[^\s:]{1,120}")

_LOVD_FIXTURE_POLICY = SourceFieldPolicy(
    action_field_allowlists={
        LOVD_FIXTURE_SOURCE_ID: {
            "normalize": (LOVD_BASIC_RECORD_FIELD,),
            "public_serialize": (LOVD_BASIC_RECORD_FIELD,),
        }
    }
)


class LovdVariantQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    installation_id: Literal["global_variome_shared_lovd"] = LOVD_INSTALLATION_ID
    genome_build: Literal["GRCh37", "GRCh38"]
    transcript_accession: str
    hgvs_c: str

    @model_validator(mode="after")
    def _validate_exact_identity(self) -> LovdVariantQuery:
        if _VERSIONED_TRANSCRIPT_RE.fullmatch(self.transcript_accession) is None:
            raise ValueError("LOVD query requires a versioned RefSeq transcript")
        if _CDNA_RE.fullmatch(self.hgvs_c) is None:
            raise ValueError("LOVD query requires canonical coding HGVS")
        return self

    @property
    def normalized_hgvs(self) -> str:
        return f"{self.transcript_accession}:{self.hgvs_c}"


class _ProjectedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str | None = None
    record_url: str | None = None
    genome_build: str | None = None
    transcript_accession: str | None = None
    hgvs_c: str | None = None
    source_edited_at: str | None = None
    record_license: str | None = None


class LovdFixtureAdapter:
    """Parse bounded synthetic LOVD schema fixtures without any network capability."""

    def __init__(self, installation: LovdInstallationSource | None = None) -> None:
        self.installation = installation or LovdInstallationSource()

    def match_json(
        self,
        document: Mapping[str, Any],
        query: LovdVariantQuery,
    ) -> LovdBasicRecordsSection:
        if not isinstance(document, Mapping):
            return self._denied("fixture_document_invalid")
        fixture_status = _safe_text(document.get("fixture_status"), max_length=40)
        installation_id = _safe_text(document.get("installation_id"), max_length=80)
        raw_records = document.get("records")
        if not isinstance(raw_records, list) or len(raw_records) > _MAX_FIXTURE_RECORDS:
            return self._denied("fixture_document_invalid")
        projected = [
            _project_mapping_record(item) for item in raw_records if isinstance(item, Mapping)
        ]
        return self._match_projected(
            fixture_status=fixture_status,
            installation_id=installation_id,
            records=projected,
            query=query,
        )

    def match_atom(self, document: str, query: LovdVariantQuery) -> LovdBasicRecordsSection:
        if not isinstance(document, str):
            return self._denied("fixture_document_invalid")
        encoded = document.encode("utf-8", errors="ignore")
        lowered = encoded.lower()
        if len(encoded) > _MAX_FIXTURE_BYTES or b"<!doctype" in lowered or b"<!entity" in lowered:
            return self._denied("fixture_document_invalid")
        try:
            root = ET.fromstring(document)
        except ET.ParseError:
            return self._denied("fixture_document_invalid")
        if root.tag != f"{{{_ATOM_NS}}}feed":
            return self._denied("fixture_document_invalid")

        entries = root.findall(f"{{{_ATOM_NS}}}entry")
        if len(entries) > _MAX_FIXTURE_RECORDS:
            return self._denied("fixture_document_invalid")
        fixture_status = _atom_text(root, "fixture_status")
        installation_id = _atom_text(root, "installation_id")
        projected = [_project_atom_record(entry) for entry in entries]
        return self._match_projected(
            fixture_status=fixture_status,
            installation_id=installation_id,
            records=projected,
            query=query,
        )

    def _match_projected(
        self,
        *,
        fixture_status: str | None,
        installation_id: str | None,
        records: list[_ProjectedRecord],
        query: LovdVariantQuery,
    ) -> LovdBasicRecordsSection:
        if fixture_status != _FIXTURE_STATUS:
            return self._denied("fixture_marker_missing")
        if installation_id != self.installation.installation_id:
            return self._denied("installation_not_allowlisted")

        matches = [
            record
            for record in records
            if record.genome_build == query.genome_build
            and record.transcript_accession == query.transcript_accession
            and record.hgvs_c == query.hgvs_c
        ]
        if not matches:
            return LovdBasicRecordsSection(
                installation=self.installation,
                status="not_found",
                warnings=["exact_normalized_hgvs_match_not_found"],
            )
        if len(matches) != 1:
            return LovdBasicRecordsSection(
                installation=self.installation,
                status="ambiguous",
                warnings=["ambiguous_exact_normalized_hgvs_match"],
            )

        match = matches[0]
        if match.record_license != _ALLOWED_RECORD_LICENSE:
            return self._denied("record_license_denied")
        observation = self._build_observation(match)
        if observation is None:
            return self._denied("matched_record_invalid")
        return LovdBasicRecordsSection(
            installation=self.installation,
            status="matched",
            observations=[observation],
            warnings=["synthetic_fixture_only", "live_lovd_access_disabled"],
        )

    def _build_observation(self, record: _ProjectedRecord) -> LovdBasicObservation | None:
        if not all(
            (
                record.record_id,
                record.record_url,
                record.genome_build,
                record.transcript_accession,
                record.hgvs_c,
                record.source_edited_at,
            )
        ):
            return None
        try:
            return LovdBasicObservation(
                source_record_id=(
                    f"{self.installation.installation_id}:variant:{record.record_id}"
                ),
                source_url=record.record_url,
                record_license=_ALLOWED_RECORD_LICENSE,
                installation=self.installation,
                genome_build=record.genome_build,
                transcript_accession=record.transcript_accession,
                hgvs_c=record.hgvs_c,
                source_edited_at=record.source_edited_at,
                policy_decisions=_policy_decisions(),
            )
        except (ValidationError, ValueError):
            return None

    def _denied(self, warning: str) -> LovdBasicRecordsSection:
        return LovdBasicRecordsSection(
            installation=self.installation,
            status="denied",
            warnings=[warning],
        )


def validated_lovd_basic_records(raw: Any) -> LovdBasicRecordsSection | None:
    """Admit only a fully validated matched fixture section into a report profile."""

    try:
        section = (
            raw
            if isinstance(raw, LovdBasicRecordsSection)
            else LovdBasicRecordsSection.model_validate(raw)
        )
    except (ValidationError, TypeError, ValueError):
        return None
    if section.status != "matched" or section.live_request_performed is not False:
        return None
    return section


def _project_mapping_record(raw: Mapping[str, Any]) -> _ProjectedRecord:
    return _ProjectedRecord(
        record_id=_safe_text(raw.get("record_id"), max_length=80),
        record_url=_safe_text(raw.get("record_url"), max_length=300),
        genome_build=_safe_text(raw.get("genome_build"), max_length=20),
        transcript_accession=_safe_text(raw.get("transcript_accession"), max_length=40),
        hgvs_c=_safe_text(raw.get("hgvs_c"), max_length=128),
        source_edited_at=_safe_text(raw.get("source_edited_at"), max_length=40),
        record_license=_safe_text(raw.get("record_license"), max_length=40),
    )


def _project_atom_record(entry: ET.Element) -> _ProjectedRecord:
    link = next(
        (
            item.get("href")
            for item in entry.findall(f"{{{_ATOM_NS}}}link")
            if item.get("rel") == "alternate"
        ),
        None,
    )
    return _ProjectedRecord(
        record_id=_atom_text(entry, "record_id"),
        record_url=_safe_text(link, max_length=300),
        genome_build=_atom_text(entry, "genome_build"),
        transcript_accession=_atom_text(entry, "transcript_accession"),
        hgvs_c=_atom_text(entry, "hgvs_c"),
        source_edited_at=_safe_text(
            entry.findtext(f"{{{_ATOM_NS}}}updated"),
            max_length=40,
        ),
        record_license=_atom_text(entry, "record_license"),
    )


def _atom_text(node: ET.Element, local_name: str) -> str | None:
    return _safe_text(node.findtext(f"{{{_LOVD_FIXTURE_NS}}}{local_name}"), max_length=300)


def _safe_text(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > max_length:
        return None
    return stripped


def _policy_decisions() -> list[SourcePolicyDecision]:
    actions = (
        "acquire",
        "normalize",
        "public_serialize",
        "cache",
        "product_export",
        "log",
        "analyze",
        "backup",
        "stage",
        "restore",
        "raw_debug",
    )
    decisions: list[SourcePolicyDecision] = []
    for action in actions:
        decision = _LOVD_FIXTURE_POLICY.decide(
            LOVD_FIXTURE_SOURCE_ID,
            LOVD_BASIC_RECORD_FIELD,
            action=action,
            product_tier=ProductTier.INTERNAL_FIXTURE,
        )
        decisions.append(
            SourcePolicyDecision(
                action=action,
                field=LOVD_BASIC_RECORD_FIELD,
                outcome="allowed" if decision.allowed else "denied",
                reason=decision.reason,
                decided_at=LOVD_POLICY_DECIDED_AT,
            )
        )
    return decisions


__all__ = [
    "LovdFixtureAdapter",
    "LovdVariantQuery",
    "validated_lovd_basic_records",
]
