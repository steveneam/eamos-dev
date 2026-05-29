from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.db import ProteinAnnotationCacheRecord, session_scope
from app.schemas.protein_annotation import ProteinDomainTrack


class ProteinAnnotationCacheRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def get(
        self,
        *,
        sequence_hash: str,
        pfam_release: str,
        hmmer_release: str,
        uniprot_release: str | None = None,
    ) -> ProteinDomainTrack | None:
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(ProteinAnnotationCacheRecord).where(
                    ProteinAnnotationCacheRecord.sequence_hash == sequence_hash,
                    ProteinAnnotationCacheRecord.pfam_release == pfam_release,
                    ProteinAnnotationCacheRecord.hmmer_release == hmmer_release,
                    ProteinAnnotationCacheRecord.uniprot_release == uniprot_release,
                )
            ).scalar_one_or_none()
            if record is None:
                return None
            return ProteinDomainTrack.model_validate(record.track or {})

    def upsert(self, track: ProteinDomainTrack) -> None:
        if (
            not track.protein_sequence_hash
            or not track.pfam_release
            or not track.hmmer_release
            or not track.cache_key
            or track.protein_length is None
        ):
            raise ValueError("protein annotation cache track is missing key fields")

        now = datetime.now(timezone.utc)
        payload = track.model_dump(mode="json")
        with session_scope(self.session_factory) as session:
            record = session.execute(
                select(ProteinAnnotationCacheRecord).where(
                    ProteinAnnotationCacheRecord.sequence_hash == track.protein_sequence_hash,
                    ProteinAnnotationCacheRecord.pfam_release == track.pfam_release,
                    ProteinAnnotationCacheRecord.hmmer_release == track.hmmer_release,
                )
            ).scalar_one_or_none()
            if record is None:
                session.add(
                    ProteinAnnotationCacheRecord(
                        sequence_hash=track.protein_sequence_hash,
                        protein_length=track.protein_length,
                        pfam_release=track.pfam_release,
                        hmmer_release=track.hmmer_release,
                        uniprot_release=track.uniprot_release,
                        cache_key=track.cache_key,
                        track=payload,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return

            record.protein_length = track.protein_length
            record.uniprot_release = track.uniprot_release
            record.cache_key = track.cache_key
            record.track = payload
            record.updated_at = now
