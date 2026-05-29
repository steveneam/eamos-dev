from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    func,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserEvidenceSubmissionRecord(Base):
    __tablename__ = "user_evidence_submissions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    variant_hgvs: Mapped[str] = mapped_column(String(255), index=True)
    submitted_pmid: Mapped[str] = mapped_column(String(16), index=True)
    curator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinvar_tracking_id: Mapped[str] = mapped_column(String(64), index=True)
    pubmed_validation: Mapped[dict] = mapped_column(JSON)
    clinvar_payload: Mapped[dict] = mapped_column(JSON)
    submission_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class SubscriptionStateRecord(Base):
    __tablename__ = "subscription_states"

    state_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    plan_key: Mapped[str] = mapped_column(String(32), default="free")
    billing_interval: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="free", index=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_event: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class ReportRecord(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    extraction_status: Mapped[str] = mapped_column(String(32))
    report_data: Mapped[dict] = mapped_column(JSON)
    review_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class RunRecord(Base):
    __tablename__ = "report_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    report_ids: Mapped[list[str]] = mapped_column(JSON)
    run_status: Mapped[str] = mapped_column(String(32), default="completed")
    review_status: Mapped[str] = mapped_column(String(32), default="pending_review")
    report_payload: Mapped[dict] = mapped_column(JSON)
    evidence: Mapped[list[dict]] = mapped_column(JSON)
    warnings: Mapped[list[str]] = mapped_column(JSON)
    review_note: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SearchDocumentRecord(Base):
    __tablename__ = "search_documents"

    doc_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    doc_type: Mapped[str] = mapped_column(String(16), index=True)
    run_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    report_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    patient_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    report_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    extraction_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    run_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    review_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    case_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    report_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    evidence_text: Mapped[str] = mapped_column(Text, default="")
    review_note: Mapped[str] = mapped_column(Text, default="")
    raw_extracted_text: Mapped[str] = mapped_column(Text, default="")
    identifier_text: Mapped[str] = mapped_column(Text, default="")
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class SearchVariantRecord(Base):
    __tablename__ = "search_variants"

    variant_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("search_documents.doc_id", ondelete="CASCADE"), index=True
    )
    gene_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gene_symbol_norm: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    transcript_hgvs: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transcript_hgvs_norm: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    protein_change: Mapped[str | None] = mapped_column(String(255), nullable=True)
    protein_change_norm: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    consequence: Mapped[str | None] = mapped_column(String(255), nullable=True)


class VariantCacheRecord(Base):
    __tablename__ = "variant_cache"

    cache_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_string: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    litvar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_publications: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publication_data: Mapped[str] = mapped_column(Text, default="{}")
    strict_genomic_cache: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class SourceCacheRecord(Base):
    __tablename__ = "source_cache"
    __table_args__ = (Index("ix_source_cache_source_key", "source", "cache_key", unique=True),)

    cache_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    cache_key: Mapped[str] = mapped_column(String(255), index=True)
    normalized_identity: Mapped[dict] = mapped_column(JSON, default=dict)
    request_identity: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), index=True)
    source_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    raw: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class ProteinAnnotationCacheRecord(Base):
    __tablename__ = "protein_annotation_cache"
    __table_args__ = (
        Index(
            "ix_protein_annotation_cache_sequence_release",
            "sequence_hash",
            "pfam_release",
            "hmmer_release",
            "uniprot_release",
            unique=True,
        ),
    )

    cache_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_hash: Mapped[str] = mapped_column(String(64), index=True)
    protein_length: Mapped[int] = mapped_column(Integer)
    pfam_release: Mapped[str] = mapped_column(String(160), index=True)
    hmmer_release: Mapped[str] = mapped_column(String(160), index=True)
    uniprot_release: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    cache_key: Mapped[str] = mapped_column(String(512), index=True)
    track: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


def _build_search_documents_fts_expression(search_documents_table):
    simple_cfg = text("'simple'")
    english_cfg = text("'english'")
    weight_a = text("'A'")
    weight_b = text("'B'")
    weight_c = text("'C'")
    weight_d = text("'D'")
    expression = func.setweight(
        func.to_tsvector(simple_cfg, func.coalesce(search_documents_table.c.identifier_text, "")),
        weight_a,
    )
    expression = expression.op("||")(
        func.setweight(
            func.to_tsvector(english_cfg, func.coalesce(search_documents_table.c.summary_text, "")),
            weight_b,
        )
    )
    expression = expression.op("||")(
        func.setweight(
            func.to_tsvector(
                english_cfg, func.coalesce(search_documents_table.c.evidence_text, "")
            ),
            weight_c,
        )
    )
    expression = expression.op("||")(
        func.setweight(
            func.to_tsvector(english_cfg, func.coalesce(search_documents_table.c.review_note, "")),
            weight_c,
        )
    )
    expression = expression.op("||")(
        func.setweight(
            func.to_tsvector(
                english_cfg, func.coalesce(search_documents_table.c.raw_extracted_text, "")
            ),
            weight_d,
        )
    )
    return expression


def _ensure_postgres_search_indexes(engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    search_documents = SearchDocumentRecord.__table__
    fts_index = Index(
        "ix_search_documents_search_text_fts",
        _build_search_documents_fts_expression(search_documents),
        postgresql_using="gin",
    )
    fts_index.create(bind=engine, checkfirst=True)


def build_engine(database_url: str):
    kwargs: dict[str, object] = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **kwargs)


def build_session_factory(database_url: str):
    engine = build_engine(database_url)
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
    )


def initialize_database(session_factory) -> None:
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(engine)
    _ensure_user_evidence_submission_payload_column(engine)
    _ensure_protein_annotation_cache_uniprot_release_column(engine)
    _ensure_postgres_search_indexes(engine)


def _ensure_user_evidence_submission_payload_column(engine) -> None:
    if "user_evidence_submissions" not in inspect(engine).get_table_names():
        return
    columns = {
        column["name"] for column in inspect(engine).get_columns("user_evidence_submissions")
    }
    if "submission_payload" in columns:
        return

    if engine.dialect.name == "postgresql":
        statement = (
            "ALTER TABLE user_evidence_submissions "
            "ADD COLUMN IF NOT EXISTS submission_payload JSONB DEFAULT '{}'::jsonb"
        )
    else:
        statement = (
            "ALTER TABLE user_evidence_submissions "
            "ADD COLUMN submission_payload JSON DEFAULT '{}'"
        )
    with engine.begin() as connection:
        connection.execute(text(statement))


def _ensure_protein_annotation_cache_uniprot_release_column(engine) -> None:
    if "protein_annotation_cache" not in inspect(engine).get_table_names():
        return
    columns = {column["name"] for column in inspect(engine).get_columns("protein_annotation_cache")}
    if "uniprot_release" in columns:
        return

    statement = "ALTER TABLE protein_annotation_cache ADD COLUMN uniprot_release VARCHAR(160)"
    with engine.begin() as connection:
        connection.execute(text(statement))


@contextmanager
def session_scope(session_factory):
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database(session_factory) -> bool:
    with session_scope(session_factory) as session:
        session.execute(text("SELECT 1"))
    return True
