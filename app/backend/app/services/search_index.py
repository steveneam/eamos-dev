from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

from app.schemas.report import UploadedReport
from app.schemas.run import PubMedArticle, ReportPayload, RunResponse, TrialMatch
from app.schemas.search import SearchDocumentWrite, SearchVariantWrite
from app.schemas.variant_library import SavedVariant, VariantPopularity

LIBRARY_VARIANT_DOC_TYPE = "library_variant"
POPULAR_VARIANT_DOC_TYPE = "popular_variant"
PUBLICATION_DOC_TYPE = "publication"
TRIAL_DOC_TYPE = "trial"
REPORT_SECTION_DOC_TYPE = "report_section"
GENE_DOC_TYPE = "gene"
SOURCE_DOC_TYPE = "source"


class SearchIndexService:
    def __init__(self, search_repo, reports_repo, run_repo) -> None:
        self.search_repo = search_repo
        self.reports_repo = reports_repo
        self.run_repo = run_repo
        self._run_loader = getattr(run_repo, "get_run", None)

    def index_report(self, report: UploadedReport, *, owner_user_id: str | None = None) -> None:
        document = self._build_report_document(report, owner_user_id=owner_user_id)
        self.search_repo.upsert_document(document)

    def index_run(
        self,
        run: RunResponse,
        reports: list[UploadedReport] | None = None,
        *,
        owner_user_id: str | None = None,
    ) -> None:
        normalized_run = self._coerce_run(run)
        effective_owner_user_id = owner_user_id or self._existing_run_owner(normalized_run.run_id)
        source_reports = reports or [
            report
            for report_id in normalized_run.report_ids
            if (report := self.reports_repo.get(report_id)) is not None
        ]
        document = self._build_run_document(
            normalized_run,
            source_reports,
            owner_user_id=effective_owner_user_id,
        )
        self.search_repo.upsert_document(document)
        self._replace_report_section_documents(
            normalized_run,
            owner_user_id=effective_owner_user_id,
        )
        for source_document in self._build_public_source_documents(normalized_run):
            self.search_repo.upsert_document(source_document)

    def refresh_run(self, run_id: str) -> None:
        run = (
            self._run_loader(run_id) if self._run_loader is not None else self.run_repo.get(run_id)
        )
        if run is None:
            return
        self.index_run(run)

    def index_saved_variant(self, variant: SavedVariant, *, owner_user_id: str) -> None:
        document = self._build_saved_variant_document(variant, owner_user_id=owner_user_id)
        self.search_repo.upsert_document(document)

    def index_saved_variants(
        self,
        variants: Sequence[SavedVariant],
        *,
        owner_user_id: str,
    ) -> None:
        for variant in variants:
            self.index_saved_variant(variant, owner_user_id=owner_user_id)

    def replace_saved_variants(
        self,
        variants: Sequence[SavedVariant],
        *,
        owner_user_id: str,
    ) -> None:
        self.search_repo.delete_owner_documents(
            doc_type=LIBRARY_VARIANT_DOC_TYPE,
            owner_user_id=owner_user_id,
        )
        self.index_saved_variants(variants, owner_user_id=owner_user_id)

    def remove_saved_variant(self, *, variant_id: str, owner_user_id: str) -> None:
        self.search_repo.delete_document(
            source_key=self._saved_variant_source_key(
                owner_user_id=owner_user_id,
                variant_id=variant_id,
            )
        )

    def index_variant_popularity(self, popularity: VariantPopularity) -> None:
        self.search_repo.upsert_document(self._build_popular_variant_document(popularity))

    def _coerce_run(self, run: RunResponse) -> RunResponse:
        if isinstance(run, RunResponse):
            return run
        if isinstance(run, dict):
            return RunResponse(**run)
        return RunResponse.model_validate(run)

    def backfill_reports_and_runs(
        self,
        *,
        dry_run: bool = True,
        owner_user_id: str | None = None,
    ) -> dict[str, object]:
        reports = self.reports_repo.list_all()
        runs = self.run_repo.list_all_runs()
        report_by_id = {report.report_id: report for report in reports}
        report_documents = [
            self._build_report_document(report, owner_user_id=owner_user_id) for report in reports
        ]
        run_documents = [
            self._build_run_document(
                run,
                [
                    report_by_id[report_id]
                    for report_id in run.report_ids
                    if report_id in report_by_id
                ],
                owner_user_id=owner_user_id,
            )
            for run in runs
        ]
        public_documents = [
            document
            for run in runs
            for document in self._build_public_source_documents(self._coerce_run(run))
        ]
        documents = self._dedupe_documents([*report_documents, *run_documents, *public_documents])
        ownerless_private_rows = sum(
            1
            for document in documents
            if document.visibility_scope == "private" and document.owner_user_id is None
        )
        if not dry_run:
            for document in documents:
                self.search_repo.upsert_document(document)
        return {
            "mode": "search_index_backfill",
            "dry_run": dry_run,
            "reports_seen": len(reports),
            "runs_seen": len(runs),
            "documents_planned": len(documents),
            "documents_indexed": 0 if dry_run else len(documents),
            "owner_user_id_provided": bool(owner_user_id),
            "ownerless_private_rows": ownerless_private_rows,
            "source_downloads_performed": False,
            "provider_calls_performed": False,
            "supabase_mutation_performed": False,
            "startup_backfill": False,
        }

    def _build_report_document(
        self,
        report: UploadedReport,
        *,
        owner_user_id: str | None = None,
    ) -> SearchDocumentWrite:
        variants = [self._build_variant_write(item) for item in report.extracted_case.variants]
        identifier_parts: list[object | None] = [
            report.report_id,
            report.filename,
            report.extracted_case.case_label,
            report.extracted_case.report_title,
        ]
        for variant in report.extracted_case.variants:
            identifier_parts.extend([variant.gene, variant.transcript_hgvs, variant.protein_change])

        summary_text = self._join_text(
            [
                report.extracted_case.patient_context,
                report.extracted_case.clinical_findings,
                report.extracted_case.summary,
            ]
        )
        raw_extracted_text = (report.raw_extracted_text or "").strip()

        return SearchDocumentWrite(
            source_key=f"report:{report.report_id}",
            doc_type="report",
            visibility_scope="private",
            owner_user_id=owner_user_id,
            report_id=report.report_id,
            filename=report.filename,
            report_kind=report.report_kind,
            extraction_status=report.extraction_status,
            case_label=report.extracted_case.case_label,
            report_title=report.extracted_case.report_title,
            summary_text=summary_text,
            evidence_text="\n".join(report.extraction_warnings),
            raw_extracted_text=raw_extracted_text,
            identifier_text=self._join_text(identifier_parts),
            search_text=self._join_text(
                [
                    *identifier_parts,
                    summary_text,
                    raw_extracted_text,
                    *report.extraction_warnings,
                ]
            ),
            variants=variants,
        )

    def _build_run_document(
        self,
        run: RunResponse,
        reports: list[UploadedReport],
        *,
        owner_user_id: str | None = None,
    ) -> SearchDocumentWrite:
        variants = self._collect_variants(reports)
        titles = [
            report.extracted_case.report_title
            for report in reports
            if report.extracted_case.report_title
        ]
        case_labels = [
            report.extracted_case.case_label
            for report in reports
            if report.extracted_case.case_label
        ]
        raw_extracted_text = "\n\n".join(
            report.raw_extracted_text.strip()
            for report in reports
            if report.raw_extracted_text and report.raw_extracted_text.strip()
        )
        summary_text = self._join_text(
            [
                run.report_payload.patient_context,
                run.report_payload.ai_clinical_summary,
                run.report_payload.clinical_phenotype,
                run.report_payload.clinical_integration,
                run.report_payload.recommendations,
                run.report_payload.limitations,
            ]
        )
        evidence_text = self._join_text(
            [
                run.report_payload.expanded_evidence,
                run.report_payload.acmg_classification,
                *run.warnings,
                *[
                    self._join_text(
                        [
                            item.source,
                            item.status,
                            *item.warnings,
                            *(item.summary.values() if getattr(item, "summary", None) else []),
                        ]
                    )
                    for item in run.evidence
                ],
            ]
        )
        identifier_parts: list[object | None] = [
            run.run_id,
            run.patient_id,
            *run.report_ids,
            *titles,
            *case_labels,
        ]
        for variant in variants:
            identifier_parts.extend(
                [variant.gene_symbol, variant.transcript_hgvs, variant.protein_change]
            )

        return SearchDocumentWrite(
            source_key=f"run:{run.run_id}",
            doc_type="run",
            visibility_scope="private",
            owner_user_id=owner_user_id,
            run_id=run.run_id,
            patient_id=run.patient_id,
            run_status=run.run_status.value,
            review_status=run.review_status.value,
            case_label=case_labels[0] if case_labels else None,
            report_title=titles[0] if titles else None,
            summary_text=summary_text,
            evidence_text=evidence_text,
            review_note=(run.review_note or "").strip(),
            raw_extracted_text=raw_extracted_text,
            identifier_text=self._join_text(identifier_parts),
            search_text=self._join_text(
                [
                    *identifier_parts,
                    summary_text,
                    evidence_text,
                    raw_extracted_text,
                    run.review_note,
                ]
            ),
            variants=variants,
        )

    def _build_public_source_documents(self, run: RunResponse) -> list[SearchDocumentWrite]:
        payload = run.report_payload
        evidence_documents: list[SearchDocumentWrite] = []
        seen_publications: set[str] = set()
        for article in self._publication_articles(payload):
            pmid = (article.pmid or "").strip()
            if not pmid or pmid in seen_publications:
                continue
            seen_publications.add(pmid)
            evidence_documents.append(self._build_publication_document(payload, article))

        seen_trials: set[str] = set()
        for trial in self._trial_rows(payload):
            nct_id = (trial.nct_id or "").strip().upper()
            if not nct_id or nct_id in seen_trials:
                continue
            seen_trials.add(nct_id)
            evidence_documents.append(self._build_trial_document(payload, trial))

        documents = [
            *evidence_documents,
            *self._build_gene_documents(evidence_documents),
            *self._build_source_vocabulary_documents(payload),
        ]
        return self._dedupe_documents(documents)

    def _replace_report_section_documents(
        self,
        run: RunResponse,
        *,
        owner_user_id: str | None,
    ) -> None:
        if not owner_user_id:
            return
        prefix = self._report_section_source_key_prefix(run.run_id)
        self.search_repo.delete_documents_by_source_key_prefix(source_key_prefix=prefix)
        for document in self._build_report_section_documents(run, owner_user_id=owner_user_id):
            self.search_repo.upsert_document(document)

    def _build_report_section_documents(
        self,
        run: RunResponse,
        *,
        owner_user_id: str,
    ) -> list[SearchDocumentWrite]:
        profile = run.report_payload.report_profile
        if profile is None:
            return []
        variants = self._variant_writes_from_payload(run.report_payload)
        documents: list[SearchDocumentWrite] = []
        for signal in profile.section_signals:
            section_id = (signal.section_id or "").strip()
            if not section_id:
                continue
            title = signal.label
            if signal.headline:
                title = f"{signal.label}: {signal.headline}"
            source_refs = list(signal.source_refs)
            data_notes = list(signal.data_notes)
            summary_text = self._join_text(
                [
                    signal.label,
                    signal.headline,
                    signal.relevance,
                    signal.source_strength,
                    signal.status,
                ]
            )
            evidence_text = self._join_text([*source_refs, *data_notes])
            identifier_text = self._join_text([run.run_id, section_id, signal.label, *source_refs])
            documents.append(
                SearchDocumentWrite(
                    source_key=(
                        f"{self._report_section_source_key_prefix(run.run_id)}"
                        f"{self._stable_token(section_id)}"
                    ),
                    doc_type=REPORT_SECTION_DOC_TYPE,
                    visibility_scope="private",
                    owner_user_id=owner_user_id,
                    run_id=run.run_id,
                    run_status=run.run_status.value,
                    review_status=run.review_status.value,
                    report_title=title,
                    summary_text=summary_text,
                    evidence_text=evidence_text,
                    identifier_text=identifier_text,
                    search_text=self._join_text(
                        [identifier_text, summary_text, evidence_text, *run.warnings]
                    ),
                    metadata={
                        "section_id": section_id,
                        "status": signal.status,
                        "relevance": signal.relevance,
                        "source_strength": signal.source_strength,
                    },
                    variants=variants,
                )
            )
        return documents

    def _build_publication_document(
        self,
        payload: ReportPayload,
        article: PubMedArticle,
    ) -> SearchDocumentWrite:
        snippet_texts = [snippet.text for snippet in article.snippets if snippet.text]
        matched_terms = [
            term
            for snippet in article.snippets
            for term in snippet.matched_terms
            if term and term.strip()
        ]
        source_tags = [str(tag) for tag in article.source_tags]
        identifier_text = self._join_text(
            [
                f"PMID {article.pmid}",
                article.pmid,
                article.pmcid,
                article.doi,
                *source_tags,
                *matched_terms,
            ]
        )
        summary_text = self._join_text([article.title, article.abstract, *snippet_texts])
        evidence_text = self._join_text(
            [
                article.authors,
                article.journal,
                article.year,
                article.publication_date,
                article.url,
                article.snippet_status,
            ]
        )
        return SearchDocumentWrite(
            source_key=f"{PUBLICATION_DOC_TYPE}:pmid:{article.pmid.strip()}",
            doc_type=PUBLICATION_DOC_TYPE,
            visibility_scope="public",
            report_title=article.title or f"PubMed {article.pmid}",
            summary_text=summary_text,
            evidence_text=evidence_text,
            identifier_text=identifier_text,
            search_text=self._join_text([identifier_text, summary_text, evidence_text]),
            metadata={
                "pmid": article.pmid.strip(),
                "pmcid": article.pmcid,
                "doi": article.doi,
                "journal": article.journal,
                "year": article.year,
                "publication_date": article.publication_date,
                "source_status": article.snippet_status,
            },
            variants=self._variant_writes_from_payload(payload, extra_terms=matched_terms),
        )

    def _build_trial_document(
        self,
        payload: ReportPayload,
        trial: TrialMatch,
    ) -> SearchDocumentWrite:
        nct_id = trial.nct_id.strip().upper()
        identifier_text = self._join_text(
            [
                nct_id,
                trial.title,
                *trial.conditions,
                *trial.interventions,
                *trial.matched_terms,
            ]
        )
        summary_text = self._join_text(
            [
                trial.title,
                trial.status,
                trial.phase,
                *trial.conditions,
                *trial.interventions,
                trial.evidence_snippet,
            ]
        )
        evidence_text = self._join_text(
            [
                trial.source_url,
                trial.match_level,
                trial.evidence_field,
                trial.last_update_posted_at,
                trial.fetched_at,
                *trial.locations,
                *trial.warnings,
            ]
        )
        return SearchDocumentWrite(
            source_key=f"{TRIAL_DOC_TYPE}:{nct_id}",
            doc_type=TRIAL_DOC_TYPE,
            visibility_scope="public",
            report_title=trial.title or nct_id,
            summary_text=summary_text,
            evidence_text=evidence_text,
            identifier_text=identifier_text,
            search_text=self._join_text([identifier_text, summary_text, evidence_text]),
            metadata={
                "nct_id": nct_id,
                "status": trial.status,
                "phase": trial.phase,
                "source_url": trial.source_url,
                "match_level": trial.match_level,
                "fetched_at": trial.fetched_at,
                "last_update_posted_at": trial.last_update_posted_at,
            },
            variants=self._variant_writes_from_payload(
                payload,
                extra_terms=[*trial.matched_terms, *trial.conditions, *trial.interventions],
            ),
        )

    def _build_gene_documents(
        self,
        public_evidence_documents: Sequence[SearchDocumentWrite],
    ) -> list[SearchDocumentWrite]:
        by_gene: dict[str, dict[str, object]] = {}
        for document in public_evidence_documents:
            document_genes: set[str] = set()
            for variant in document.variants:
                gene = (variant.gene_symbol_norm or variant.gene_symbol or "").strip().upper()
                if not gene:
                    continue
                document_genes.add(gene)
                entry = by_gene.setdefault(
                    gene,
                    {
                        "publication_count": 0,
                        "trial_count": 0,
                        "titles": set(),
                        "aliases": set(),
                    },
                )
                titles = entry["titles"]
                aliases = entry["aliases"]
                if isinstance(titles, set) and document.report_title:
                    titles.add(document.report_title)
                if isinstance(aliases, set):
                    for value in (
                        variant.gene_symbol,
                        variant.transcript_hgvs,
                        variant.protein_change,
                    ):
                        if value:
                            aliases.add(value)
            for gene in document_genes:
                entry = by_gene[gene]
                if document.doc_type == PUBLICATION_DOC_TYPE:
                    entry["publication_count"] = int(entry["publication_count"]) + 1
                elif document.doc_type == TRIAL_DOC_TYPE:
                    entry["trial_count"] = int(entry["trial_count"]) + 1

        documents: list[SearchDocumentWrite] = []
        for gene, entry in sorted(by_gene.items()):
            titles = sorted(str(title) for title in entry["titles"] if str(title).strip())
            aliases = sorted(str(alias) for alias in entry["aliases"] if str(alias).strip())
            publication_count = int(entry["publication_count"])
            trial_count = int(entry["trial_count"])
            summary_text = self._join_text(
                [
                    f"{gene} source-backed public gene vocabulary",
                    f"{publication_count} indexed publication(s)" if publication_count else None,
                    f"{trial_count} indexed trial(s)" if trial_count else None,
                    *titles[:6],
                ]
            )
            identifier_text = self._join_text([gene, *aliases])
            documents.append(
                SearchDocumentWrite(
                    source_key=f"{GENE_DOC_TYPE}:{self._stable_token(gene)}",
                    doc_type=GENE_DOC_TYPE,
                    visibility_scope="public",
                    report_title=gene,
                    summary_text=summary_text,
                    evidence_text=self._join_text(titles),
                    identifier_text=identifier_text,
                    search_text=self._join_text([identifier_text, summary_text, *titles]),
                    metadata={
                        "gene": gene,
                        "publication_count": publication_count,
                        "trial_count": trial_count,
                        "source_status": "source_backed_public_payload",
                        "target_href": f"/report?q={gene}",
                    },
                    variants=[
                        SearchVariantWrite(
                            gene_symbol=gene,
                            gene_symbol_norm=gene,
                        )
                    ],
                )
            )
        return documents

    def _build_source_vocabulary_documents(
        self,
        payload: ReportPayload,
    ) -> list[SearchDocumentWrite]:
        source_rows: dict[str, dict[str, object | None]] = {}
        if payload.report_data_currency is not None:
            for source in payload.report_data_currency.sources:
                source_id = (source.source or "").strip()
                if not source_id:
                    continue
                source_rows[source_id] = {
                    "source_id": source_id,
                    "label": source.label,
                    "materialized_at": source.materialized_at,
                    "upstream_released_at": source.upstream_released_at,
                    "tier": source.tier,
                    "status": source.status,
                    "staleness_days": source.staleness_days,
                    "source_version": source.source_version,
                }

        for source_id, source_version in payload.source_versions.items():
            normalized_source_id = (source_id or "").strip()
            if not normalized_source_id or normalized_source_id == "source_version":
                continue
            source_rows.setdefault(
                normalized_source_id,
                {
                    "source_id": normalized_source_id,
                    "label": normalized_source_id,
                    "materialized_at": None,
                    "upstream_released_at": None,
                    "tier": None,
                    "status": None,
                    "staleness_days": None,
                    "source_version": source_version,
                },
            )

        documents: list[SearchDocumentWrite] = []
        for source_id, row in sorted(source_rows.items()):
            label = str(row.get("label") or source_id)
            source_version = row.get("source_version")
            status = row.get("status")
            tier = row.get("tier")
            identifier_text = self._join_text([source_id, label, source_version])
            summary_text = self._join_text(
                [
                    label,
                    "Eamos source metadata",
                    f"Status: {status}" if status else None,
                    f"Version: {source_version}" if source_version else None,
                ]
            )
            evidence_text = self._join_text(
                [
                    f"Tier: {tier}" if tier else None,
                    (
                        f"Materialized at: {row.get('materialized_at')}"
                        if row.get("materialized_at")
                        else None
                    ),
                    (
                        f"Upstream released at: {row.get('upstream_released_at')}"
                        if row.get("upstream_released_at")
                        else None
                    ),
                    (
                        f"Staleness days: {row.get('staleness_days')}"
                        if row.get("staleness_days") is not None
                        else None
                    ),
                ]
            )
            documents.append(
                SearchDocumentWrite(
                    source_key=f"{SOURCE_DOC_TYPE}:{self._stable_token(source_id)}",
                    doc_type=SOURCE_DOC_TYPE,
                    visibility_scope="public",
                    report_title=label,
                    summary_text=summary_text,
                    evidence_text=evidence_text,
                    identifier_text=identifier_text,
                    search_text=self._join_text([identifier_text, summary_text, evidence_text]),
                    metadata={
                        "source_id": source_id,
                        "label": label,
                        "status": str(status) if status else None,
                        "tier": str(tier) if tier else None,
                        "source_version": str(source_version) if source_version else None,
                        "materialized_at": (
                            str(row.get("materialized_at")) if row.get("materialized_at") else None
                        ),
                        "upstream_released_at": (
                            str(row.get("upstream_released_at"))
                            if row.get("upstream_released_at")
                            else None
                        ),
                        "staleness_days": (
                            int(row["staleness_days"])
                            if isinstance(row.get("staleness_days"), int)
                            else None
                        ),
                        "source_status": "report_data_currency",
                    },
                )
            )
        return documents

    def _publication_articles(self, payload: ReportPayload) -> list[PubMedArticle]:
        articles: list[PubMedArticle] = []
        if payload.publications_literature is not None:
            articles.extend(payload.publications_literature.articles)
        articles.extend(payload.pubmed_articles)
        return articles

    def _trial_rows(self, payload: ReportPayload) -> list[TrialMatch]:
        if payload.report_profile is None or payload.report_profile.therapies_trials is None:
            return []
        return list(payload.report_profile.therapies_trials.trial_rows)

    def _variant_writes_from_payload(
        self,
        payload: ReportPayload,
        *,
        extra_terms: Sequence[str] = (),
    ) -> list[SearchVariantWrite]:
        rows: list[SearchVariantWrite] = []
        seen: set[tuple[str | None, str | None, str | None]] = set()
        for variant in payload.variant_summary_rows:
            self._append_variant_write(rows, seen, self._build_variant_write(variant))
        for term in extra_terms:
            variant = self._variant_write_from_term(term)
            if variant is not None:
                self._append_variant_write(rows, seen, variant)
        return rows

    def _append_variant_write(
        self,
        rows: list[SearchVariantWrite],
        seen: set[tuple[str | None, str | None, str | None]],
        variant: SearchVariantWrite,
    ) -> None:
        key = (variant.gene_symbol_norm, variant.transcript_hgvs_norm, variant.protein_change_norm)
        if key == (None, None, None):
            return
        if key in seen:
            return
        seen.add(key)
        rows.append(variant)

    def _variant_write_from_term(self, value: str) -> SearchVariantWrite | None:
        text = (value or "").strip()
        if not text:
            return None
        lowered = text.lower()
        gene = text.upper() if self._looks_like_gene_symbol(text) else None
        transcript_hgvs = text if lowered.startswith("c.") or ":c." in lowered else None
        protein_change = None
        if lowered.startswith("p."):
            protein_change = text
        else:
            protein_match = re.search(r"\bp\.[A-Za-z0-9_*?=]+", text)
            if protein_match:
                protein_change = protein_match.group(0)
        if not gene and not transcript_hgvs and not protein_change:
            return None
        return SearchVariantWrite(
            gene_symbol=gene,
            gene_symbol_norm=gene,
            transcript_hgvs=transcript_hgvs,
            transcript_hgvs_norm=self._normalize_identifier(transcript_hgvs),
            protein_change=protein_change,
            protein_change_norm=self._normalize_identifier(protein_change),
        )

    def _looks_like_gene_symbol(self, value: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{1,15}", value.strip()))

    def _build_saved_variant_document(
        self,
        variant: SavedVariant,
        *,
        owner_user_id: str,
    ) -> SearchDocumentWrite:
        title = (
            " ".join(
                part.strip() for part in (variant.gene, variant.variant) if part and part.strip()
            )
            or variant.query
        )
        classification = (variant.classification or "").replace("_", " ").strip()
        transcript_hgvs = self._saved_variant_transcript_hgvs(variant)
        protein_change = self._saved_variant_protein_change(variant)
        variant_write = SearchVariantWrite(
            gene_symbol=variant.gene,
            gene_symbol_norm=variant.gene.upper() if variant.gene else None,
            transcript_hgvs=transcript_hgvs,
            transcript_hgvs_norm=self._normalize_identifier(transcript_hgvs),
            protein_change=protein_change,
            protein_change_norm=self._normalize_identifier(protein_change),
            consequence=None,
        )
        identifier_parts = [
            variant.id,
            variant.gene,
            variant.variant,
            variant.query,
            variant.hgvs_full,
            protein_change,
        ]
        summary_text = self._join_text(
            [
                variant.query,
                f"Classification: {classification}" if classification else None,
                variant.hgvs_full,
            ]
        )
        raw_text = (variant.raw or "").strip()
        return SearchDocumentWrite(
            source_key=self._saved_variant_source_key(
                owner_user_id=owner_user_id,
                variant_id=variant.id,
            ),
            doc_type=LIBRARY_VARIANT_DOC_TYPE,
            visibility_scope="private",
            owner_user_id=owner_user_id,
            report_title=title,
            summary_text=summary_text,
            raw_extracted_text=raw_text,
            identifier_text=self._join_text(identifier_parts),
            search_text=self._join_text([*identifier_parts, summary_text, raw_text]),
            metadata={
                "query": variant.query,
                "variant_id": variant.id,
                "classification": variant.classification,
                "hgvs_full": variant.hgvs_full,
                "saved_at": variant.savedAt,
            },
            variants=[variant_write],
        )

    def _build_popular_variant_document(
        self,
        popularity: VariantPopularity,
    ) -> SearchDocumentWrite:
        query_id = popularity.query_id.strip().lower()
        title = self._display_variant_query(query_id)
        variant_write = self._variant_write_from_popular_query(query_id)
        identifier_text = self._join_text([query_id, title, variant_write.gene_symbol])
        last_viewed = popularity.last_viewed.isoformat() if popularity.last_viewed else None
        summary_text = self._join_text(
            [
                title,
                f"Public variant view count: {popularity.view_count}",
                f"Last viewed: {last_viewed}" if last_viewed else None,
            ]
        )
        evidence_text = "Eamos public variant view counter"
        return SearchDocumentWrite(
            source_key=self._popular_variant_source_key(query_id=query_id),
            doc_type=POPULAR_VARIANT_DOC_TYPE,
            visibility_scope="public",
            report_title=title,
            summary_text=summary_text,
            evidence_text=evidence_text,
            identifier_text=identifier_text,
            search_text=self._join_text([identifier_text, summary_text, evidence_text]),
            metadata={
                "query": query_id,
                "query_id": query_id,
                "view_count": popularity.view_count,
                "last_viewed": last_viewed,
                "source_status": "public_view_counter",
            },
            variants=[variant_write],
        )

    def _collect_variants(self, reports: list[UploadedReport]) -> list[SearchVariantWrite]:
        seen: set[tuple[str | None, str | None, str | None]] = set()
        rows: list[SearchVariantWrite] = []
        for report in reports:
            for variant in report.extracted_case.variants:
                key = (variant.gene, variant.transcript_hgvs, variant.protein_change)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(self._build_variant_write(variant))
        return rows

    def _build_variant_write(self, variant) -> SearchVariantWrite:
        gene = (variant.gene or "").strip() or None
        transcript_hgvs = (variant.transcript_hgvs or "").strip() or None
        protein_change = (variant.protein_change or "").strip() or None
        return SearchVariantWrite(
            gene_symbol=gene,
            gene_symbol_norm=gene.upper() if gene else None,
            transcript_hgvs=transcript_hgvs,
            transcript_hgvs_norm=self._normalize_identifier(transcript_hgvs),
            protein_change=protein_change,
            protein_change_norm=self._normalize_identifier(protein_change),
            consequence=(variant.consequence or "").strip() or None,
        )

    def _join_text(self, items: Sequence[object | None]) -> str:
        return "\n".join(str(item).strip() for item in items if str(item or "").strip())

    def _dedupe_documents(
        self,
        documents: Sequence[SearchDocumentWrite],
    ) -> list[SearchDocumentWrite]:
        by_source_key: dict[str, SearchDocumentWrite] = {}
        for document in documents:
            by_source_key[document.source_key] = document
        return list(by_source_key.values())

    def _normalize_identifier(self, value: str | None) -> str | None:
        if not value:
            return None
        return "".join(value.split()).lower()

    def _saved_variant_source_key(self, *, owner_user_id: str, variant_id: str) -> str:
        digest = hashlib.sha256(f"{owner_user_id}\x1f{variant_id}".encode("utf-8")).hexdigest()
        return f"{LIBRARY_VARIANT_DOC_TYPE}:{digest[:24]}"

    def _popular_variant_source_key(self, *, query_id: str) -> str:
        digest = hashlib.sha256(query_id.encode("utf-8")).hexdigest()
        return f"{POPULAR_VARIANT_DOC_TYPE}:{digest[:24]}"

    def _report_section_source_key_prefix(self, run_id: str) -> str:
        return f"{REPORT_SECTION_DOC_TYPE}:{run_id}:"

    def _stable_token(self, value: str) -> str:
        token = re.sub(r"[^a-z0-9_.:-]+", "-", value.lower()).strip("-")
        if token:
            return token[:48]
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    def _existing_run_owner(self, run_id: str) -> str | None:
        return self.search_repo.owner_for_source_key(source_key=f"run:{run_id}")

    def _saved_variant_transcript_hgvs(self, variant: SavedVariant) -> str | None:
        for value in (variant.hgvs_full, variant.variant, variant.query, variant.raw):
            text = (value or "").strip()
            lowered = text.lower()
            if lowered.startswith("c.") or ":c." in lowered:
                return text
        return None

    def _saved_variant_protein_change(self, variant: SavedVariant) -> str | None:
        for value in (variant.variant, variant.query, variant.raw):
            text = (value or "").strip()
            if text.lower().startswith("p."):
                return text
            match = re.search(r"\bp\.[A-Za-z0-9_*?=]+", text)
            if match:
                return match.group(0)
        return None

    def _variant_write_from_popular_query(self, query_id: str) -> SearchVariantWrite:
        gene = None
        transcript_hgvs = None
        parts = query_id.split()
        if parts and self._looks_like_gene_symbol(parts[0]):
            gene = parts[0].upper()
        for part in parts[1:]:
            if part.lower().startswith("c."):
                transcript_hgvs = self._display_cdna(part)
                break
        return SearchVariantWrite(
            gene_symbol=gene,
            gene_symbol_norm=gene,
            transcript_hgvs=transcript_hgvs,
            transcript_hgvs_norm=self._normalize_identifier(transcript_hgvs),
            protein_change=None,
            protein_change_norm=None,
        )

    def _display_variant_query(self, query_id: str) -> str:
        parts = query_id.split()
        if not parts:
            return query_id
        display_parts = [parts[0].upper()]
        for part in parts[1:]:
            if part.lower().startswith("c."):
                display_parts.append(self._display_cdna(part))
            else:
                display_parts.append(part)
        return " ".join(display_parts)

    def _display_cdna(self, value: str) -> str:
        text = value.strip()
        if not text.lower().startswith("c."):
            return text
        return f"{text[:2].lower()}{text[2:].upper()}"
