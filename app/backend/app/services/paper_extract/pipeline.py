"""Build the frozen Paper V2 document/evidence graph from request-lifetime text."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Sequence

from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.paper_variants import (
    PaperDocumentBundleV2,
    PaperDocumentExtractionV2,
    PaperDocumentMetadataV2,
    PaperMentionResolutionV2,
    PaperPageExtractionQualityV2,
)
from app.services.paper_extract.document import PaperInputDocument, bundle_input_digest
from app.services.paper_extract.grammar import DetectedMention, extract_page_records
from app.services.paper_extract.metadata import bibliographic_metadata

ALGORITHM_VERSION = "2.0.0"
VALIDATION_MATRIX_ID = "paper-synthetic-v2"
MAX_BUNDLE_MENTIONS = 500


@dataclass(frozen=True, slots=True)
class PaperExtractionDraft:
    bundle: PaperDocumentBundleV2
    page_quality: tuple[PaperPageExtractionQualityV2, ...]
    records: tuple[DetectedMention, ...]
    deterministic_digest: str
    execution_disclosure: CapabilityExecutionDisclosureV2
    warnings: tuple[str, ...]

    def finalize(
        self, resolutions: Sequence[PaperMentionResolutionV2]
    ) -> PaperDocumentExtractionV2:
        return PaperDocumentExtractionV2(
            bundle=self.bundle,
            deterministic_digest=self.deterministic_digest,
            page_quality=list(self.page_quality),
            mentions=[record.mention for record in self.records],
            resolutions=list(resolutions),
            ai_adjudications=[],
            execution_disclosure=self.execution_disclosure,
            warnings=list(self.warnings),
        )


def build_extraction_draft(
    documents: Sequence[PaperInputDocument],
    *,
    bundle_id: str = "paper-request",
) -> PaperExtractionDraft:
    if not documents:
        raise ValueError("paper bundle requires at least one document")
    metadata_rows: list[PaperDocumentMetadataV2] = []
    page_quality: list[PaperPageExtractionQualityV2] = []
    records: list[DetectedMention] = []
    warnings: list[str] = []
    mention_limit_reached = False
    for document in documents:
        metadata_rows.append(
            PaperDocumentMetadataV2(
                document_id=document.document_id,
                role=document.role,
                kind=document.kind,
                filename=document.safe_filename,
                media_type=document.media_type,
                size_bytes=document.size_bytes,
                sha256=document.sha256,
                page_count=len(document.pages) if document.kind == "pdf" else None,
                extraction_engine=document.extraction_engine,
                extraction_engine_version=document.extraction_engine_version,
                bibliographic_metadata=bibliographic_metadata(document),
                warnings=list(document.warnings),
            )
        )
        warnings.extend(document.warnings)
        for page in document.pages:
            if document.kind == "pdf":
                page_quality.append(
                    PaperPageExtractionQualityV2(
                        document_id=document.document_id,
                        page_number=page.page_number,
                        quality=page.quality,
                        extracted_character_count=len(page.text),
                        replacement_character_ratio=page.replacement_character_ratio,
                        warnings=list(page.warnings),
                    )
                )
            if page.quality in {"good", "degraded"} and not mention_limit_reached:
                remaining_with_sentinel = MAX_BUNDLE_MENTIONS - len(records) + 1
                page_records = extract_page_records(
                    document_id=document.document_id,
                    page_number=page.page_number,
                    text=page.text,
                    max_records=remaining_with_sentinel,
                )
                records.extend(page_records)
                if len(records) > MAX_BUNDLE_MENTIONS:
                    del records[MAX_BUNDLE_MENTIONS:]
                    mention_limit_reached = True
                    warnings.append(f"paper_mention_limit_exceeded:{MAX_BUNDLE_MENTIONS}")

    input_digest = bundle_input_digest(documents)
    bundle = PaperDocumentBundleV2(
        bundle_id=bundle_id,
        documents=metadata_rows,
        input_digest=input_digest,
    )
    deterministic_digest = _deterministic_digest(input_digest, records)
    disclosure = CapabilityExecutionDisclosureV2(
        capability_id="paper_l1_l3",
        claim="Deterministic page-preserving variant mention extraction and context routing.",
        execution="eamos_local",
        algorithm_id="eamos_paper_extract",
        algorithm_version=ALGORITHM_VERSION,
        input_scope=f"sha256:{input_digest}",
        source_status="not_required",
        applicability="applicable",
        validation_status="validated",
        validation_matrix_id=VALIDATION_MATRIX_ID,
        retention="request_lifetime",
        consent_required=False,
        warnings=[],
        requirements=[],
    )
    return PaperExtractionDraft(
        bundle=bundle,
        page_quality=tuple(page_quality),
        records=tuple(records),
        deterministic_digest=deterministic_digest,
        execution_disclosure=disclosure,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _deterministic_digest(input_digest: str, records: Sequence[DetectedMention]) -> str:
    payload = {
        "algorithm": f"eamos_paper_extract@{ALGORITHM_VERSION}",
        "input_digest": input_digest,
        "mentions": [
            {
                "mention_id": record.mention.mention_id,
                "canonical_notation": record.canonical_notation,
                "context": record.mention.biological_context,
                "layer": record.mention.extraction_layer,
                "document_id": record.mention.span.document_id,
                "page": record.mention.span.page_number,
                "start": record.mention.span.start_character,
                "end": record.mention.span.end_character,
                "genes": record.mention.gene_evidence,
                "transcripts": record.mention.transcript_evidence,
            }
            for record in records
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
