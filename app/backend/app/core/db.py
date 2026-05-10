from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import Boolean, JSON, DateTime, ForeignKey, Index, Integer, String, Text, create_engine, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = 'users'

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
            func.to_tsvector(english_cfg, func.coalesce(search_documents_table.c.evidence_text, "")),
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
    _ensure_postgres_search_indexes(engine)


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
