from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.cli import eamos_literature_embed_materialize as cli
from app.cli import eamos_literature_embed_preflight as preflight_cli
from app.core.config import Settings
from app.services.ai_gateway.retrieval import (
    LiteratureEmbeddingStore,
    LiteratureRetriever,
    LiteratureSourceRecord,
    materialize_literature_embeddings,
)

DIM = 4


class FakeEmbedder:
    """Returns a fixed vector for every input (one per item), no network."""

    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.calls: list[list[str]] = []

    def embed(self, inputs: list[str]) -> list[list[float]]:
        self.calls.append(list(inputs))
        return [list(self.vector) for _ in inputs]


class BoomEmbedder:
    def embed(self, inputs: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding provider down")


def _record(
    pmid: str, genes: list[str], *, snippet: str = "", title: str = "Title"
) -> LiteratureSourceRecord:
    return LiteratureSourceRecord(
        pmid=pmid,
        genes=[g.upper() for g in genes],
        title=title,
        snippet=snippet,
        embed_text="",
        year=2022,
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        license_profile="cc_by",
    )


def _store(
    tmp_path: Path, rows: list[tuple[LiteratureSourceRecord, list[float]]]
) -> LiteratureEmbeddingStore:
    store = LiteratureEmbeddingStore(
        tmp_path / "lit.sqlite", manifest_path=tmp_path / "lit.manifest.json"
    )
    store.write(rows, embedding_model="test-embed", embedding_dim=DIM, source_version="test-v1")
    return store


def _retriever(store, *, top_k=2, min_score=0.5, snippet_max_chars=600) -> LiteratureRetriever:
    return LiteratureRetriever(
        store=store,
        embedder=FakeEmbedder([1.0, 0.0, 0.0, 0.0]),
        top_k=top_k,
        min_score=min_score,
        snippet_max_chars=snippet_max_chars,
    )


# --- retrieval: gene filter + top-k + floor (D4) ---------------------------


def test_retrieve_filters_by_gene_applies_floor_and_top_k(tmp_path: Path) -> None:
    store = _store(
        tmp_path,
        [
            (_record("P1", ["RPE65"], snippet="abstract one"), [1.0, 0.0, 0.0, 0.0]),  # cos 1.0
            (_record("P2", ["RPE65"], snippet="abstract two"), [0.8, 0.6, 0.0, 0.0]),  # cos 0.8
            (
                _record("P3", ["RPE65"], snippet="orthogonal"),
                [0.0, 1.0, 0.0, 0.0],
            ),  # cos 0.0 < floor
            (_record("P4", ["ABCA4"], snippet="other gene"), [1.0, 0.0, 0.0, 0.0]),  # wrong gene
        ],
    )
    hits = _retriever(store, top_k=2, min_score=0.5).retrieve("what about RPE65?", ["RPE65"])

    assert [h.pmid for h in hits] == ["P1", "P2"]  # gene-filtered, floor-pruned, top-2 by score
    assert hits[0].score >= hits[1].score


def test_retrieve_min_score_floor_prunes_weak_matches(tmp_path: Path) -> None:
    store = _store(
        tmp_path,
        [
            (_record("P1", ["RPE65"]), [1.0, 0.0, 0.0, 0.0]),  # cos 1.0
            (_record("P2", ["RPE65"]), [0.8, 0.6, 0.0, 0.0]),  # cos 0.8 < 0.9 floor
        ],
    )
    hits = _retriever(store, top_k=5, min_score=0.9).retrieve("q", ["RPE65"])
    assert [h.pmid for h in hits] == ["P1"]


def test_retrieve_empty_when_no_gene_match(tmp_path: Path) -> None:
    store = _store(tmp_path, [(_record("P1", ["RPE65"]), [1.0, 0.0, 0.0, 0.0])])
    assert _retriever(store).retrieve("q", ["BRCA1"]) == []


def test_retrieve_empty_when_no_genes(tmp_path: Path) -> None:
    store = _store(tmp_path, [(_record("P1", ["RPE65"]), [1.0, 0.0, 0.0, 0.0])])
    assert _retriever(store).retrieve("q", []) == []


def test_retrieve_empty_when_store_missing(tmp_path: Path) -> None:
    store = LiteratureEmbeddingStore(tmp_path / "absent.sqlite")
    assert _retriever(store).retrieve("q", ["RPE65"]) == []


def test_retrieve_empty_when_embedding_fails(tmp_path: Path) -> None:
    store = _store(tmp_path, [(_record("P1", ["RPE65"]), [1.0, 0.0, 0.0, 0.0])])
    retriever = LiteratureRetriever(
        store=store, embedder=BoomEmbedder(), top_k=5, min_score=0.0, snippet_max_chars=600
    )
    assert retriever.retrieve("q", ["RPE65"]) == []  # never raises


# --- retrieval: snippet safety (D5 defense-in-depth) -----------------------


def test_retrieve_drops_forbidden_title_and_empties_forbidden_snippet(tmp_path: Path) -> None:
    store = _store(
        tmp_path,
        [
            (
                _record("CLEAN", ["RPE65"], snippet="clean abstract", title="Clean title"),
                [1.0, 0, 0, 0],
            ),
            (
                _record("SNIP", ["RPE65"], snippet="leak patient_id 42", title="Ok title"),
                [1.0, 0, 0, 0],
            ),
            (
                _record("TITLE", ["RPE65"], snippet="fine", title="Bearer vck_abcdefghijklmnop"),
                [1.0, 0, 0, 0],
            ),
        ],
    )
    hits = _retriever(store, top_k=5, min_score=0.0).retrieve("q", ["RPE65"])

    by_pmid = {h.pmid: h for h in hits}
    assert "TITLE" not in by_pmid  # forbidden title → whole row dropped
    assert by_pmid["CLEAN"].snippet == "clean abstract"
    assert by_pmid["SNIP"].snippet == ""  # forbidden snippet → emptied, row kept


def test_retrieve_sanitizes_overlong_snippet(tmp_path: Path) -> None:
    store = _store(tmp_path, [(_record("P1", ["RPE65"], snippet="A" * 100), [1.0, 0, 0, 0])])
    hits = _retriever(store, top_k=1, min_score=0.0, snippet_max_chars=20).retrieve("q", ["RPE65"])
    assert hits[0].snippet.endswith("…")
    assert len(hits[0].snippet) == 21


def test_query_returns_empty_on_dim_mismatch(tmp_path: Path) -> None:
    store = _store(tmp_path, [(_record("P1", ["RPE65"]), [1.0, 0, 0, 0])])
    assert store.query(["RPE65"], [1.0, 0.0], min_score=0.0) == []  # 2-dim query vs 4-dim store


# --- materialization (read pubmed_local → embed → write store) -------------


def _make_pubmed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript("""
        create table pubmed_article (
          pmid text primary key, title text not null, year text,
          pubmed_url text, license_profile text, abstract_policy text,
          abstract_text text, mesh_terms_json text,
          is_retracted integer not null default 0
        );
        create table pubmed_article_term (
          pmid text, term_type text, term_norm text
        );
        """)
    conn.execute(
        "insert into pubmed_article values (?,?,?,?,?,?,?,?,0)",
        (
            "111",
            "RPE65 retinal study",
            "2022",
            "https://pubmed.ncbi.nlm.nih.gov/111/",
            "cc_by",
            "licensed_text_persisted",
            "Full abstract about RPE65.",
            json.dumps(["Retina"]),
        ),
    )
    conn.execute("insert into pubmed_article_term values ('111','gene','rpe65')")
    conn.execute(
        "insert into pubmed_article values (?,?,?,?,?,?,?,?,0)",
        (
            "222",
            "ABCA4 review",
            "2019",
            "https://pubmed.ncbi.nlm.nih.gov/222/",
            "publisher_copyright",
            "metadata_only_license_unverified",
            None,
            json.dumps(["Macula"]),
        ),
    )
    conn.execute("insert into pubmed_article_term values ('222','gene','abca4')")
    # geneless → skipped
    conn.execute(
        "insert into pubmed_article values (?,?,?,?,?,?,?,?,0)",
        ("333", "No gene", "2020", "u", "cc0", "licensed_text_persisted", "abs", "[]"),
    )
    # retracted → skipped
    conn.execute(
        "insert into pubmed_article values (?,?,?,?,?,?,?,?,1)",
        ("444", "Retracted", "2021", "u", "cc_by", "licensed_text_persisted", "abs", "[]"),
    )
    conn.execute("insert into pubmed_article_term values ('444','gene','rpe65')")
    conn.commit()
    conn.close()


def _materialize_settings(**over) -> Settings:
    base = {"jwt_secret": "lit-test", "rag_embedding_dim": DIM, "rag_embedding_model": "test-embed"}
    base.update(over)
    return Settings(**base)


def test_materialize_respects_license_gene_scope_and_retraction(tmp_path: Path) -> None:
    src = tmp_path / "pubmed.sqlite"
    out = tmp_path / "lit.sqlite"
    _make_pubmed_db(src)

    result = materialize_literature_embeddings(
        _materialize_settings(),
        embedder=FakeEmbedder([1.0, 0.0, 0.0, 0.0]),
        source_db_path=src,
        output_path=out,
        manifest_path=tmp_path / "lit.manifest.json",
        source_version="cli-v1",
    )

    assert result.ready is True
    assert result.article_count == 2  # 333 geneless + 444 retracted skipped
    assert result.licensed_snippet_count == 1  # only 111 persists abstract text
    assert result.metadata_only_count == 1  # 222 metadata-only
    assert result.gene_pair_count == 2

    store = LiteratureEmbeddingStore(out)
    rpe = store.query(["RPE65"], [1.0, 0.0, 0.0, 0.0], min_score=0.0)
    assert [h.pmid for h in rpe] == ["111"]
    assert rpe[0].snippet == "Full abstract about RPE65."  # D3: licensed body retrieved
    assert rpe[0].year == 2022

    abca = store.query(["ABCA4"], [1.0, 0.0, 0.0, 0.0], min_score=0.0)
    assert [h.pmid for h in abca] == ["222"]
    assert abca[0].snippet == ""  # D3: metadata-only row carries no body text


def test_materialize_missing_source_is_not_ready(tmp_path: Path) -> None:
    result = materialize_literature_embeddings(
        _materialize_settings(),
        embedder=FakeEmbedder([1.0, 0.0, 0.0, 0.0]),
        source_db_path=tmp_path / "absent.sqlite",
        output_path=tmp_path / "lit.sqlite",
    )
    assert result.ready is False
    assert "missing" in result.message


# --- CLI ------------------------------------------------------------------


def test_cli_emits_sanitized_report(tmp_path: Path, capsys) -> None:
    src = tmp_path / "pubmed.sqlite"
    out = tmp_path / "lit.sqlite"
    _make_pubmed_db(src)
    # CLI builds Settings with default 1536-dim, so the fake must match.
    fake = FakeEmbedder([1.0] + [0.0] * 1535)

    code = cli.main(
        [
            "--source-db",
            str(src),
            "--output",
            str(out),
            "--manifest",
            str(tmp_path / "lit.manifest.json"),
            "--source-version",
            "cli-v1",
        ],
        embedder=fake,
    )

    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "literature_embed_materialize"
    assert report["materialization"]["article_count"] == 2
    assert report["materialization"]["ready"] is True
    assert report["guardrails"]["network"] == {"used": True, "provider": "vercel_ai_gateway"}
    assert report["guardrails"]["startup_download"] == "not_used"
    assert out.is_file()


# --- preflight ------------------------------------------------------------


def test_store_inspect_reports_ready_and_missing(tmp_path: Path) -> None:
    store = _store(tmp_path, [(_record("P1", ["RPE65"]), [1.0, 0.0, 0.0, 0.0])])
    ready = store.inspect()
    assert ready.ready is True
    assert ready.status == "ready"
    assert ready.article_count == 1
    assert ready.embedding_dim == DIM

    missing = LiteratureEmbeddingStore(tmp_path / "absent.sqlite").inspect()
    assert missing.ready is False
    assert missing.status == "db_missing"


def test_preflight_cli_require_ready_exit_codes(tmp_path: Path, capsys) -> None:
    out = tmp_path / "lit.sqlite"
    _store(tmp_path, [(_record("P1", ["RPE65"]), [1.0, 0.0, 0.0, 0.0])])  # writes lit.sqlite

    assert preflight_cli.main(["--db-path", str(out), "--require-ready"]) == 0
    ready_report = json.loads(capsys.readouterr().out)
    assert ready_report["ready"] is True
    assert ready_report["article_count"] == 1

    assert (
        preflight_cli.main(["--db-path", str(tmp_path / "absent.sqlite"), "--require-ready"]) == 2
    )
    missing_report = json.loads(capsys.readouterr().out)
    assert missing_report["status"] == "db_missing"
    assert missing_report["network_used"] is False
