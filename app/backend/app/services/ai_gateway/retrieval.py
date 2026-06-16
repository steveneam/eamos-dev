"""Literature RAG retrieval for the variant-chat gateway path.

Local-first vector store (decision D1=B, docs/ai-gateway-rag/spec.md §3): the
embeddings live in a SQLite asset on the Render disk beside `pubmed_local` — no
Supabase coupling, no per-chat network hop to a managed vector DB. The store keeps
each embedding as a float32 BLOB and scores candidates with brute-force cosine over
the *gene-filtered* set; the corpus is gene-scoped, so the candidate set per query
is small and an ANN index (sqlite-vec / pgvector) would only add a native/managed
dependency for no win. Question + corpus embeddings go through the AI Gateway broker
(decision D2=A): `openai/text-embedding-3-small`, 1536-dim.

The store is built offline by `cli/eamos_literature_embed_materialize.py`, never at
startup/deploy. Retrieval is inert unless `rag_enabled` and `llm_provider == "gateway"`.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from array import array
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Iterator, Protocol

from app.services.ai_gateway.guard import contains_forbidden_token

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "literature-embedding-v1"
CLI_VERSION = "literature-embed-cli-v1"
SOURCE_VERSION_PREFIX = "literature-embedding"
LITERATURE_QUERY_MAX_CANDIDATES = 2_000


# -- public retrieval record ------------------------------------------------


@dataclass
class RetrievedLiterature:
    """One retrieved abstract, shaped for the bounded-context contract (§6)."""

    pmid: str
    title: str
    snippet: str
    year: int | None
    source_url: str | None
    score: float

    def to_context_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"pmid": self.pmid, "title": self.title, "score": self.score}
        if self.snippet:
            out["snippet"] = self.snippet
        if self.year is not None:
            out["year"] = self.year
        if self.source_url:
            out["source_url"] = self.source_url
        return out


# -- embedding seam ---------------------------------------------------------


class Embedder(Protocol):
    """Anything that turns texts into vectors (gateway broker, or a test fake)."""

    def embed(self, inputs: list[str]) -> list[list[float]]: ...


class GatewayEmbedder:
    """Adapts the AI Gateway broker's `/embeddings` to the `Embedder` seam."""

    def __init__(self, engine: Any, model: str) -> None:
        self._engine = engine
        self._model = model

    def embed(self, inputs: list[str]) -> list[list[float]]:
        return self._engine.embed(inputs, model=self._model)


# -- vector helpers (pure stdlib; portable across Windows/Linux) -------------


def _pack_vector(vector: Iterable[float]) -> bytes:
    return array("f", vector).tobytes()


def _unpack_vector(blob: bytes) -> array:
    arr = array("f")
    arr.frombytes(blob)
    return arr


def _vector_norm(vector: Iterable[float]) -> float:
    total = 0.0
    for value in vector:
        total += value * value
    return math.sqrt(total)


def _cosine(a: Iterable[float], b: Iterable[float], *, norm_a: float | None = None) -> float:
    dot = 0.0
    computed_norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        if norm_a is None:
            computed_norm_a += x * x
        norm_b += y * y
    left_norm = math.sqrt(computed_norm_a) if norm_a is None else norm_a
    if left_norm == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / left_norm / math.sqrt(norm_b)


@lru_cache(maxsize=1)
def _numpy_module() -> Any | None:
    try:
        import numpy as np
    except ImportError:
        return None
    return np


def _sanitize_snippet(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    cleaned = "".join(ch for ch in text if ch in ("\n", "\t") or (ch >= " " and ch != "\x7f"))
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "…"
    return cleaned


def _normalize_genes(genes: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for gene in genes:
        norm = str(gene or "").strip().upper()
        if norm and norm not in seen:
            seen.append(norm)
    return seen


def _connect_readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# -- materialization input record -------------------------------------------


@dataclass
class LiteratureSourceRecord:
    pmid: str
    genes: list[str]
    title: str
    snippet: str
    embed_text: str
    year: int | None
    source_url: str | None
    license_profile: str


# -- local SQLite vector store ----------------------------------------------


@dataclass
class LiteratureStoreInspection:
    ready: bool
    status: str
    article_count: int = 0
    gene_pair_count: int = 0
    embedding_model: str = ""
    embedding_dim: int = 0
    source_version: str = ""
    message: str = ""


class LiteratureEmbeddingStore:
    """Local-first SQLite vector store for gene-scoped literature embeddings."""

    def __init__(self, db_path: Path, *, manifest_path: Path | None = None) -> None:
        self.db_path = db_path
        self.manifest_path = manifest_path

    # readiness -----------------------------------------------------------

    def inspect(self) -> LiteratureStoreInspection:
        if not self.db_path.is_file():
            return LiteratureStoreInspection(
                False, "db_missing", message="literature embedding store is missing"
            )
        try:
            with closing(_connect_readonly(self.db_path)) as conn:
                manifest = conn.execute("select * from literature_manifest where id = 1").fetchone()
                if manifest is None:
                    return LiteratureStoreInspection(
                        False, "manifest_missing", message="manifest row is missing"
                    )
                article_count = conn.execute(
                    "select count(*) as c from literature_embedding"
                ).fetchone()["c"]
                gene_pair_count = conn.execute(
                    "select count(*) as c from literature_gene"
                ).fetchone()["c"]
        except sqlite3.DatabaseError:
            return LiteratureStoreInspection(False, "db_unreadable", message="store is unreadable")
        return LiteratureStoreInspection(
            True,
            "ready",
            article_count=article_count,
            gene_pair_count=gene_pair_count,
            embedding_model=str(manifest["embedding_model"]),
            embedding_dim=int(manifest["embedding_dim"]),
            source_version=str(manifest["source_version"]),
            message="ready",
        )

    # read path -----------------------------------------------------------

    def query(
        self, genes: list[str], embedding: list[float], *, min_score: float
    ) -> list[RetrievedLiterature]:
        """Return all gene-filtered rows scoring >= `min_score`, sorted high→low.

        Read-only and defensive: a missing/unreadable store, or a dim mismatch
        between the query embedding and the materialized corpus, yields `[]` so
        the chat falls back to report-only grounding instead of erroring.
        """
        if not genes or not embedding or not self.db_path.is_file():
            return []
        np = _numpy_module()
        if np is not None:
            query_vector = np.asarray(embedding, dtype=np.float32)
            query_norm = float(np.linalg.norm(query_vector))
        else:
            query_vector = array("f", embedding)
            query_norm = _vector_norm(query_vector)
        if query_norm == 0.0:
            return []

        try:
            with closing(_connect_readonly(self.db_path)) as conn:
                manifest = conn.execute(
                    "select embedding_dim from literature_manifest where id = 1"
                ).fetchone()
                if manifest is None or int(manifest["embedding_dim"]) != len(embedding):
                    logger.warning(
                        "literature store embedding dim mismatch (store=%s, query=%s)",
                        None if manifest is None else manifest["embedding_dim"],
                        len(embedding),
                    )
                    return []
                placeholders = ",".join("?" * len(genes))
                rows = conn.execute(
                    f"""
                    select distinct e.pmid, e.title, e.snippet, e.year, e.source_url, e.embedding
                    from literature_embedding e
                    join literature_gene g on g.pmid = e.pmid
                    where g.gene in ({placeholders})
                    order by e.pmid
                    limit ?
                    """,
                    (*tuple(genes), LITERATURE_QUERY_MAX_CANDIDATES),
                )
                scored: list[tuple[float, sqlite3.Row]] = []
                for row in rows:
                    if np is not None:
                        vector = np.frombuffer(row["embedding"], dtype=np.float32)
                        if vector.shape[0] != query_vector.shape[0]:
                            continue
                        vector_norm = float(np.linalg.norm(vector))
                        if vector_norm == 0.0:
                            continue
                        score = float(np.dot(query_vector, vector) / query_norm / vector_norm)
                    else:
                        vector = _unpack_vector(row["embedding"])
                        if len(vector) != len(query_vector):
                            continue
                        score = _cosine(query_vector, vector, norm_a=query_norm)
                    if score < min_score:
                        continue
                    scored.append((score, row))
        except sqlite3.DatabaseError:
            logger.warning("literature store unreadable", exc_info=True)
            return []

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedLiterature(
                pmid=row["pmid"],
                title=row["title"],
                snippet=row["snippet"] or "",
                year=row["year"],
                source_url=row["source_url"],
                score=round(score, 4),
            )
            for score, row in scored
        ]

    # write path (offline materialization) --------------------------------

    def write(
        self,
        records: list[tuple[LiteratureSourceRecord, list[float]]],
        *,
        embedding_model: str,
        embedding_dim: int,
        source_version: str,
    ) -> dict[str, int]:
        """Atomically build the store from (record, vector) pairs.

        Writes to a temp file beside the target and renames into place so a
        partial run never leaves a half-built store on the Render disk.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.db_path.with_name(self.db_path.name + ".tmp")
        if temp_path.exists():
            temp_path.unlink()

        gene_pair_count = 0
        with closing(sqlite3.connect(temp_path)) as conn:
            conn.executescript(_SCHEMA_SQL)
            for record, vector in records:
                if len(vector) != embedding_dim:
                    raise ValueError(
                        f"embedding dim {len(vector)} != expected {embedding_dim} "
                        f"for pmid {record.pmid}"
                    )
                conn.execute(
                    """
                    insert or replace into literature_embedding
                    (pmid, title, snippet, year, source_url, license, embedding)
                    values (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.pmid,
                        record.title,
                        record.snippet,
                        record.year,
                        record.source_url,
                        record.license_profile,
                        _pack_vector(vector),
                    ),
                )
                for gene in record.genes:
                    conn.execute(
                        "insert or ignore into literature_gene (pmid, gene) values (?, ?)",
                        (record.pmid, gene),
                    )
                    gene_pair_count += 1
            checksum = _logical_checksum(records)
            conn.execute(
                """
                insert into literature_manifest
                (id, schema_version, source_version, cli_version, embedding_model,
                 embedding_dim, article_count, gene_pair_count, materialized_at,
                 checksum_algorithm, checksum_value)
                values (1, ?, ?, ?, ?, ?, ?, ?, ?, 'sha256', ?)
                """,
                (
                    SCHEMA_VERSION,
                    source_version,
                    CLI_VERSION,
                    embedding_model,
                    embedding_dim,
                    len(records),
                    gene_pair_count,
                    datetime.now(timezone.utc).isoformat(),
                    checksum,
                ),
            )
            conn.commit()

        temp_path.replace(self.db_path)
        if self.manifest_path is not None:
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            self.manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "source_version": source_version,
                        "cli_version": CLI_VERSION,
                        "embedding_model": embedding_model,
                        "embedding_dim": embedding_dim,
                        "article_count": len(records),
                        "gene_pair_count": gene_pair_count,
                        "checksum_algorithm": "sha256",
                        "checksum_value": checksum,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        return {"article_count": len(records), "gene_pair_count": gene_pair_count}


_SCHEMA_SQL = """
create table literature_embedding (
  pmid text primary key,
  title text not null,
  snippet text not null default '',
  year integer,
  source_url text,
  license text not null default '',
  embedding blob not null
);
create table literature_gene (
  pmid text not null references literature_embedding(pmid) on delete cascade,
  gene text not null,
  primary key (pmid, gene)
);
create index idx_literature_gene on literature_gene(gene);
create table literature_manifest (
  id integer primary key check (id = 1),
  schema_version text not null,
  source_version text not null,
  cli_version text not null,
  embedding_model text not null,
  embedding_dim integer not null,
  article_count integer not null,
  gene_pair_count integer not null,
  materialized_at text not null,
  checksum_algorithm text not null,
  checksum_value text not null
);
"""


def _logical_checksum(
    records: list[tuple[LiteratureSourceRecord, list[float]]],
) -> str:
    digest = sha256()
    for record, _ in sorted(records, key=lambda item: item[0].pmid):
        genes = ",".join(sorted(record.genes))
        digest.update(f"{record.pmid}|{genes}\n".encode("utf-8"))
    return digest.hexdigest()


# -- runtime retriever ------------------------------------------------------


class LiteratureRetriever:
    """Embeds the question, queries the local store, sanitizes, returns top-k."""

    def __init__(
        self,
        *,
        store: LiteratureEmbeddingStore,
        embedder: Embedder,
        top_k: int,
        min_score: float,
        snippet_max_chars: int,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.min_score = min_score
        self.snippet_max_chars = snippet_max_chars

    def retrieve(self, question: str, genes: Iterable[str]) -> list[RetrievedLiterature]:
        normalized = _normalize_genes(genes)
        if not normalized or not question.strip():
            return []
        try:
            vectors = self.embedder.embed([question])
        except Exception:  # provider/transport boundary — never fail the turn
            logger.warning("question embedding failed; skipping retrieval", exc_info=True)
            return []
        if not vectors or not vectors[0]:
            return []

        candidates = self.store.query(normalized, vectors[0], min_score=self.min_score)

        results: list[RetrievedLiterature] = []
        for candidate in candidates:
            if contains_forbidden_token(candidate.title):
                continue  # drop one unsafe row, don't fail the whole turn
            snippet = _sanitize_snippet(candidate.snippet, self.snippet_max_chars)
            if snippet and contains_forbidden_token(snippet):
                snippet = ""
            results.append(
                RetrievedLiterature(
                    pmid=candidate.pmid,
                    title=candidate.title,
                    snippet=snippet,
                    year=candidate.year,
                    source_url=candidate.source_url,
                    score=candidate.score,
                )
            )
            if len(results) >= self.top_k:
                break
        return results


def build_literature_retriever(
    settings: Any,
    *,
    engine: Any = None,
    store: LiteratureEmbeddingStore | None = None,
    embedder: Embedder | None = None,
) -> LiteratureRetriever | None:
    """Build the retriever, or None when RAG is inert.

    Returns None unless `rag_enabled` and `llm_provider == "gateway"` with a key
    set, so the mock/OpenAI chat paths are untouched. The `engine`/`store`/
    `embedder` seams let tests inject fakes (no network, no real corpus)."""
    if (
        not getattr(settings, "rag_enabled", False)
        or settings.llm_provider != "gateway"
        or not settings.ai_gateway_api_key
    ):
        return None

    if embedder is None:
        if engine is None:
            from app.services.ai_gateway.engine import AIGatewayEngine

            engine = AIGatewayEngine(
                api_key=settings.ai_gateway_api_key,
                model=settings.ai_gateway_model,
                provider_order=settings.ai_gateway_provider_order,
                base_url=settings.ai_gateway_base_url,
                timeout_seconds=settings.ai_gateway_timeout_seconds,
                max_retries=settings.ai_gateway_max_retries,
            )
        embedder = GatewayEmbedder(engine, settings.rag_embedding_model)

    if store is None:
        store = LiteratureEmbeddingStore(
            _resolve_path(settings, settings.rag_sqlite_path),
            manifest_path=_resolve_path(settings, settings.rag_manifest_path),
        )

    return LiteratureRetriever(
        store=store,
        embedder=embedder,
        top_k=settings.rag_top_k,
        min_score=settings.rag_min_score,
        snippet_max_chars=settings.rag_snippet_max_chars,
    )


def inspect_literature_store(settings: Any) -> LiteratureStoreInspection:
    return LiteratureEmbeddingStore(
        _resolve_path(settings, settings.rag_sqlite_path),
        manifest_path=_resolve_path(settings, settings.rag_manifest_path),
    ).inspect()


def _resolve_path(settings: Any, path: Path) -> Path:
    return path if path.is_absolute() else settings.backend_root / path


# -- offline materialization (read pubmed_local → embed → write store) -------


@dataclass
class MaterializeResult:
    ready: bool
    article_count: int = 0
    gene_pair_count: int = 0
    licensed_snippet_count: int = 0
    metadata_only_count: int = 0
    skipped_no_gene_count: int = 0
    embedding_model: str = ""
    embedding_dim: int = 0
    source_version: str = ""
    message: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_sanitized_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "article_count": self.article_count,
            "gene_pair_count": self.gene_pair_count,
            "licensed_snippet_count": self.licensed_snippet_count,
            "metadata_only_count": self.metadata_only_count,
            "skipped_no_gene_count": self.skipped_no_gene_count,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "source_version": self.source_version,
            "message": self.message,
            "warnings": list(self.warnings),
        }


def _coerce_year(value: Any) -> int | None:
    text = str(value or "").strip()
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None


def _iter_source_records(
    source_db_path: Path, *, snippet_max_chars: int
) -> Iterator[LiteratureSourceRecord]:
    with closing(_connect_readonly(source_db_path)) as conn:
        articles = conn.execute("""
            select pmid, title, year, pubmed_url, license_profile, abstract_policy,
                   abstract_text, mesh_terms_json
            from pubmed_article
            where is_retracted = 0
            """).fetchall()
        for article in articles:
            pmid = str(article["pmid"])
            gene_rows = conn.execute(
                "select term_norm from pubmed_article_term "
                "where pmid = ? and term_type = 'gene'",
                (pmid,),
            ).fetchall()
            genes = _normalize_genes(row["term_norm"] for row in gene_rows)
            if not genes:
                continue  # gene-scoped retrieval can't surface a geneless article

            title = str(article["title"] or "").strip()
            # D3: persist/retrieve abstract body only where the license policy
            # already permits it; metadata-only rows contribute title + keywords.
            abstract = (
                article["abstract_text"]
                if article["abstract_policy"] == "licensed_text_persisted"
                else None
            )
            keywords = _json_str_list(article["mesh_terms_json"])
            parts = [title]
            if abstract:
                parts.append(abstract)
            if keywords:
                parts.append("Keywords: " + ", ".join(keywords))
            embed_text = "\n\n".join(part for part in parts if part)
            snippet = _sanitize_snippet(abstract, snippet_max_chars) if abstract else ""

            yield LiteratureSourceRecord(
                pmid=pmid,
                genes=genes,
                title=title,
                snippet=snippet,
                embed_text=embed_text,
                year=_coerce_year(article["year"]),
                source_url=article["pubmed_url"],
                license_profile=str(article["license_profile"] or ""),
            )


def _json_str_list(value: Any) -> list[str]:
    try:
        data = json.loads(value) if isinstance(value, str) else []
    except (TypeError, ValueError):
        return []
    return (
        [str(item).strip() for item in data if str(item).strip()] if isinstance(data, list) else []
    )


def materialize_literature_embeddings(
    settings: Any,
    *,
    embedder: Embedder,
    source_db_path: Path | None = None,
    output_path: Path | None = None,
    manifest_path: Path | None = None,
    source_version: str | None = None,
    batch_size: int = 64,
) -> MaterializeResult:
    """Read license-permitted gene-scoped articles from pubmed_local, embed them
    through the gateway (D2=A), and write the local vector store (D1=B)."""
    source = source_db_path or _resolve_path(settings, settings.pubmed_local_sqlite_path)
    out = output_path or _resolve_path(settings, settings.rag_sqlite_path)
    manifest = manifest_path or _resolve_path(settings, settings.rag_manifest_path)
    model = settings.rag_embedding_model
    dim = settings.rag_embedding_dim
    version = source_version or f"{SOURCE_VERSION_PREFIX}-{datetime.now(timezone.utc):%Y%m%d}"

    if not source.is_file():
        return MaterializeResult(
            ready=False,
            embedding_model=model,
            embedding_dim=dim,
            source_version=version,
            message="pubmed_local source SQLite is missing",
        )

    records = list(_iter_source_records(source, snippet_max_chars=settings.rag_snippet_max_chars))
    if not records:
        return MaterializeResult(
            ready=False,
            embedding_model=model,
            embedding_dim=dim,
            source_version=version,
            message="no gene-scoped articles to embed",
        )

    vectors: list[list[float]] = []
    texts = [record.embed_text for record in records]
    for start in range(0, len(texts), batch_size):
        vectors.extend(embedder.embed(texts[start : start + batch_size]))
    if len(vectors) != len(records):
        return MaterializeResult(
            ready=False,
            embedding_model=model,
            embedding_dim=dim,
            source_version=version,
            message=f"embedder returned {len(vectors)} vectors for {len(records)} records",
        )

    paired = list(zip(records, vectors))
    store = LiteratureEmbeddingStore(out, manifest_path=manifest)
    counts = store.write(paired, embedding_model=model, embedding_dim=dim, source_version=version)

    licensed = sum(1 for record in records if record.snippet)
    return MaterializeResult(
        ready=True,
        article_count=counts["article_count"],
        gene_pair_count=counts["gene_pair_count"],
        licensed_snippet_count=licensed,
        metadata_only_count=len(records) - licensed,
        embedding_model=model,
        embedding_dim=dim,
        source_version=version,
        message="materialized",
    )
