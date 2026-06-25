from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.db import build_session_factory, initialize_database
from app.repos.report_cache_repo import ReportCacheRepo
from app.repos.variant_cache_repo import VariantCacheRepo
from app.rules.clinic_rules import ClinicRules
from app.schemas.lookup import LookupRequest, LookupSectionFetchRequest
from app.services.lookup_service import (
    LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING,
    LEGACY_REPORT_SHELL_CACHE_READ_WARNING,
    PUBLICATION_DATA_CACHE_VERSION,
    REPORT_SECTION_CACHE_VERSION,
    REPORT_SHELL_CACHE_VERSION,
    LookupService,
)

pytestmark = pytest.mark.report_cache_contract


def test_table_report_shell_wins_over_legacy_variant_publication_data(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    variant_repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    variant_repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="legacy",
        total_publications=0,
        publication_data={"publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )
    variant_repo.update_report_shell(
        "RPE65:c.260A>G",
        report_shell={
            "report_shell_cache_version": REPORT_SHELL_CACHE_VERSION,
            "summary": _summary_payload(
                header={"gene": "LEGACY", "cdna": "c.260A>G"},
                warnings=["legacy_fixture_summary"],
            ),
        },
    )
    report_repo.upsert_report_shell(
        "RPE65:c.260A>G",
        normalized_identity=_identity("RPE65:c.260A>G"),
        schema_version=REPORT_SHELL_CACHE_VERSION,
        payload=_summary_payload(header={"gene": "RPE65", "cdna": "c.260A>G"}),
        ttl_days=30,
    )
    service = _service(
        variant_repo=variant_repo,
        report_repo=report_repo,
        tmp_path=tmp_path,
    )

    summary = service.lookup_summary(LookupRequest(gene="RPE65", cdna="c.260A>G"))

    assert summary.header == {"gene": "RPE65", "cdna": "c.260A>G"}
    assert LEGACY_REPORT_SHELL_CACHE_READ_WARNING not in summary.warnings


def test_table_report_sections_win_over_legacy_variant_publication_data(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    variant_repo = VariantCacheRepo(session_factory)
    report_repo = ReportCacheRepo(session_factory)
    variant_repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="legacy",
        total_publications=0,
        publication_data={"publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )
    variant_repo.update_report_sections(
        "RPE65:c.260A>G",
        report_sections={
            "report_section_cache_version": REPORT_SECTION_CACHE_VERSION,
            "response": _sections_payload(
                status="missing",
                warnings=["legacy_fixture_sections"],
                section_warnings=["legacy_publications_missing"],
            ),
        },
    )
    report_repo.upsert_report_sections(
        "RPE65:c.260A>G",
        normalized_identity=_identity("RPE65:c.260A>G"),
        schema_version=REPORT_SECTION_CACHE_VERSION,
        response_payload=_sections_payload(
            status="available",
            payload={"articles": [{"pmid": "1", "title": "table hit"}]},
        ),
        ttl_days=30,
    )
    service = _service(
        variant_repo=variant_repo,
        report_repo=report_repo,
        tmp_path=tmp_path,
    )

    response = service.lookup_sections(
        LookupSectionFetchRequest(gene="RPE65", cdna="c.260A>G", include=["publications"])
    )

    assert response.sections["publications"].status == "available"
    assert response.sections["publications"].payload == {
        "articles": [{"pmid": "1", "title": "table hit"}]
    }
    assert LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING not in response.warnings


def test_legacy_publication_data_shell_read_is_explicitly_marked(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    variant_repo = VariantCacheRepo(session_factory)
    variant_repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="legacy",
        total_publications=0,
        publication_data={"publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )
    variant_repo.update_report_shell(
        "RPE65:c.260A>G",
        report_shell={
            "report_shell_cache_version": REPORT_SHELL_CACHE_VERSION,
            "summary": _summary_payload(warnings=["legacy_fixture_summary"]),
        },
    )

    summary = _service(variant_repo=variant_repo, tmp_path=tmp_path).lookup_summary(
        LookupRequest(gene="RPE65", cdna="c.260A>G")
    )

    assert summary.warnings == [
        "legacy_fixture_summary",
        LEGACY_REPORT_SHELL_CACHE_READ_WARNING,
    ]


def test_legacy_publication_data_sections_read_is_explicitly_marked(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path)
    variant_repo = VariantCacheRepo(session_factory)
    variant_repo.upsert(
        "RPE65:c.260A>G",
        litvar_id="legacy",
        total_publications=0,
        publication_data={"publication_data_cache_version": PUBLICATION_DATA_CACHE_VERSION},
        strict_genomic_cache={"variant": {"genomic_hg38": "1-68444869-T-C"}},
    )
    variant_repo.update_report_sections(
        "RPE65:c.260A>G",
        report_sections={
            "report_section_cache_version": REPORT_SECTION_CACHE_VERSION,
            "response": _sections_payload(warnings=["legacy_fixture_sections"]),
        },
    )

    response = _service(variant_repo=variant_repo, tmp_path=tmp_path).lookup_sections(
        LookupSectionFetchRequest(gene="RPE65", cdna="c.260A>G", include=["publications"])
    )

    assert response.warnings == [
        "legacy_fixture_sections",
        LEGACY_REPORT_SECTIONS_CACHE_READ_WARNING,
    ]


def _session_factory(tmp_path: Path):
    session_factory = build_session_factory(
        f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}"
    )
    initialize_database(session_factory)
    return session_factory


def _service(
    *,
    variant_repo: VariantCacheRepo,
    tmp_path: Path,
    report_repo: ReportCacheRepo | None = None,
) -> LookupService:
    return LookupService(
        {},
        ClinicRules(),
        variant_cache_repo=variant_repo,
        report_cache_repo=report_repo,
        settings=Settings(
            database_url=f"sqlite+pysqlite:///{(tmp_path / 'cache.db').as_posix()}",
            jwt_secret="test-secret",
            use_real_apis=True,
        ),
    )


def _identity(query: str) -> dict:
    gene, _, cdna = query.partition(":")
    return {
        "identity_version": 1,
        "query_string": query,
        "species": "human",
        "genome_build": "GRCh38",
        "gene": gene,
        "cdna": cdna,
        "request_identity": {"query": query},
    }


def _summary_payload(*, header: dict | None = None, warnings: list[str] | None = None) -> dict:
    return {
        "query": "RPE65:c.260A>G",
        "species": "human",
        "header": header or {"gene": "RPE65", "cdna": "c.260A>G"},
        "tiles": [],
        "lazy_sections": [],
        "warnings": list(warnings or []),
    }


def _sections_payload(
    *,
    status: str = "missing",
    payload: dict | None = None,
    warnings: list[str] | None = None,
    section_warnings: list[str] | None = None,
) -> dict:
    return {
        "query": "RPE65:c.260A>G",
        "species": "human",
        "sections": {
            "publications": {
                "section_id": "publications",
                "status": status,
                "payload": payload,
                "freshness": {},
                "warnings": list(section_warnings or []),
            },
        },
        "warnings": list(warnings or []),
    }
