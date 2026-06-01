from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel

DEFAULT_SECTIONS = ("pills", "popfreq", "publications", "trials")
SECTION_ORDER = (
    "pills",
    "popfreq",
    "publications",
    "trials",
    "clinical",
    "acmg",
    "disease",
    "gene",
    "protein",
)

ASSERT_FAIL_VERDICTS = {"unsupported", "contradicted"}
NO_OVERCLAIM_FAIL_VERDICTS = {"contradicted"}

_ACMG_CODE_RE = re.compile(
    r"^(PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])(?:_[A-Za-z][A-Za-z0-9]*)?$"
)
_ACMG_AXIS_OPPOSITES = {
    "PM2": {"BS1", "BA1"},
    "BS1": {"PM2"},
    "BA1": {"PM2"},
    "PP3": {"BP4"},
    "BP4": {"PP3"},
    "PS3": {"BS3"},
    "BS3": {"PS3"},
}

_CODON_TO_AA3 = {
    "TTT": "Phe",
    "TTC": "Phe",
    "TTA": "Leu",
    "TTG": "Leu",
    "TCT": "Ser",
    "TCC": "Ser",
    "TCA": "Ser",
    "TCG": "Ser",
    "TAT": "Tyr",
    "TAC": "Tyr",
    "TAA": "Ter",
    "TAG": "Ter",
    "TGT": "Cys",
    "TGC": "Cys",
    "TGA": "Ter",
    "TGG": "Trp",
    "CTT": "Leu",
    "CTC": "Leu",
    "CTA": "Leu",
    "CTG": "Leu",
    "CCT": "Pro",
    "CCC": "Pro",
    "CCA": "Pro",
    "CCG": "Pro",
    "CAT": "His",
    "CAC": "His",
    "CAA": "Gln",
    "CAG": "Gln",
    "CGT": "Arg",
    "CGC": "Arg",
    "CGA": "Arg",
    "CGG": "Arg",
    "ATT": "Ile",
    "ATC": "Ile",
    "ATA": "Ile",
    "ATG": "Met",
    "ACT": "Thr",
    "ACC": "Thr",
    "ACA": "Thr",
    "ACG": "Thr",
    "AAT": "Asn",
    "AAC": "Asn",
    "AAA": "Lys",
    "AAG": "Lys",
    "AGT": "Ser",
    "AGC": "Ser",
    "AGA": "Arg",
    "AGG": "Arg",
    "GTT": "Val",
    "GTC": "Val",
    "GTA": "Val",
    "GTG": "Val",
    "GCT": "Ala",
    "GCC": "Ala",
    "GCA": "Ala",
    "GCG": "Ala",
    "GAT": "Asp",
    "GAC": "Asp",
    "GAA": "Glu",
    "GAG": "Glu",
    "GGT": "Gly",
    "GGC": "Gly",
    "GGA": "Gly",
    "GGG": "Gly",
}


def evaluate_claims(
    payload: Any,
    evidence_map: Mapping[str, Any] | None,
    statuses: Mapping[str, str] | None,
    *,
    sections: Sequence[str] | str | None = None,
) -> dict[str, Any]:
    """Bind report claims to source facts without fetching or recomputing evidence."""
    payload_dict = _as_dict(payload)
    evidence = _as_dict(evidence_map or {})
    source_statuses = {str(key): str(value) for key, value in (statuses or {}).items()}
    selected_sections = _normalize_sections(sections)

    section_payloads: list[dict[str, Any]] = []
    for section in selected_sections:
        if section == "pills":
            section_payloads.append(_pills_section(payload_dict, evidence, source_statuses))
        elif section == "popfreq":
            section_payloads.append(_popfreq_section(payload_dict, evidence, source_statuses))
        elif section == "publications":
            section_payloads.append(_publications_section(payload_dict, evidence, source_statuses))
        elif section == "trials":
            section_payloads.append(_trials_section(payload_dict, evidence, source_statuses))
        elif section == "clinical":
            section_payloads.append(_clinical_section(payload_dict, evidence, source_statuses))
        elif section == "acmg":
            section_payloads.append(_acmg_section(payload_dict, evidence, source_statuses))
        elif section == "disease":
            section_payloads.append(_disease_section(payload_dict, evidence, source_statuses))
        elif section == "gene":
            section_payloads.append(_gene_section(payload_dict, evidence, source_statuses))
        elif section == "protein":
            section_payloads.append(_protein_section(payload_dict, evidence, source_statuses))

    claims = [claim for section in section_payloads for claim in section["claims"]]
    return {
        "sections": section_payloads,
        "summary": _summary(claims),
    }


def build_assertion(
    sections: Sequence[Mapping[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    fail_verdicts = NO_OVERCLAIM_FAIL_VERDICTS if mode == "no_overclaim" else ASSERT_FAIL_VERDICTS
    failed = [
        str(claim.get("claim_id"))
        for section in sections
        for claim in section.get("claims", [])
        if claim.get("verdict") in fail_verdicts
    ]
    return {
        "mode": mode,
        "passed": not failed,
        "failed_claim_ids": failed,
    }


def build_demo_audit(
    sections: Sequence[Mapping[str, Any]],
    source_statuses: Mapping[str, str],
) -> dict[str, Any]:
    by_name = {str(section.get("section")): section for section in sections}
    blocking: list[str] = []
    completeness: dict[str, str] = {}
    primary_source_statuses = {
        "popfreq": source_statuses.get("gnomad", "missing"),
        "clinical": source_statuses.get("clinical_consensus")
        or source_statuses.get("clingen")
        or source_statuses.get("clinvar", "missing"),
        "publications": source_statuses.get("litvar2") or source_statuses.get("pubmed", "missing"),
        "trials": source_statuses.get("clinical_trials", "missing"),
    }

    for section_name, status in primary_source_statuses.items():
        completeness[section_name] = "complete" if status in {"live", "cache"} else status
        if status not in {"live", "cache"}:
            blocking.append(f"{section_name}.source_status:{status}")

    for section_name in ("popfreq", "clinical", "publications", "trials"):
        section = by_name.get(section_name)
        variant_claims = [
            claim
            for claim in (section or {}).get("claims", [])
            if claim.get("claim_level") == "variant_specific"
        ]
        if not variant_claims:
            blocking.append(f"{section_name}.variant_specific_claims:0")

    for section in sections:
        for claim in section.get("claims", []):
            if claim.get("verdict") == "contradicted":
                blocking.append(f"{claim.get('claim_id')}:contradicted")
            if section.get("section") == "trials" and claim.get("verdict") == "unsupported":
                blocking.append(f"{claim.get('claim_id')}:unsupported")

    return {
        "allowed_as_primary_demo_sample": not blocking,
        "completeness": completeness,
        "blocking": _dedupe(blocking),
        "metric_sources": primary_source_statuses,
    }


def resolved_from_payload(payload: Any) -> dict[str, Any]:
    payload_dict = _as_dict(payload)
    row = _first_item(payload_dict.get("variant_summary_rows"))
    header = _profile(payload_dict).get("header") or {}
    return {
        "gene": _first_text(header.get("gene"), row.get("gene")),
        "transcript_hgvs": _first_text(header.get("cdna"), row.get("transcript_hgvs")),
        "protein_change": _first_text(header.get("protein_change"), row.get("protein_change")),
        "variant_id": _first_text(
            (payload_dict.get("population_frequency_detail") or {}).get("variant_id"),
            header.get("genomic_hg38"),
            row.get("genomic_hg38"),
        ),
        "genomic_hg38": _first_text(header.get("genomic_hg38"), row.get("genomic_hg38")),
    }


def _pills_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    cards = (payload.get("call_cards") or {}).get("cards") or []
    for card in _dicts(cards):
        card_id = str(card.get("card_id") or "unknown")
        source_status = _source_status_for_card(card, statuses)
        claims.append(
            _claim(
                claim_id=f"pills.{card_id}.primary_label",
                rendered_text=str(card.get("primary_label") or ""),
                rendered_in="call_card.primary_label",
                claim_kind="call_card_primary_label",
                claim_level=(
                    "variant_specific" if source_status not in {"missing", ""} else "unsupported"
                ),
                verdict="supported" if source_status not in {"missing", ""} else "unverifiable",
                source_status=source_status,
                provenance=_string_list(card.get("provenance")),
                warnings=_string_list(card.get("warnings")),
            )
        )
        for badge in _dicts(card.get("support_badges")):
            text = str(badge.get("text") or "")
            code = _acmg_code(text)
            if code:
                claims.append(
                    _evaluate_acmg_badge_claim(
                        claim_id=f"pills.{card_id}.{code.lower()}_badge",
                        rendered_text=text,
                        rendered_in="call_card.support_badge",
                        claim_kind="acmg_code_badge",
                        code=code,
                        payload=payload,
                        evidence_map=evidence_map,
                        statuses=statuses,
                        provenance=_string_list(card.get("provenance")),
                    )
                )
            else:
                claims.append(
                    _metric_badge_claim(
                        card_id=card_id,
                        text=text,
                        badge=badge,
                        card=card,
                        payload=payload,
                        statuses=statuses,
                    )
                )
    return _section("pills", "Call Cards", _combined_status(statuses, statuses.keys()), claims)


def _popfreq_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    detail = _dict_or_empty(payload.get("population_frequency_detail"))
    card = _card(payload, "population_frequency")
    claims: list[dict[str, Any]] = []
    source_status = statuses.get("gnomad", detail.get("source_status") or "missing")
    provenance = _string_list(card.get("provenance")) or _source_urls(detail)
    warnings = _string_list(detail.get("warnings"))
    warnings.extend(_population_band_warnings(detail))

    if card:
        has_frequency = detail.get("allele_frequency") is not None
        claims.append(
            _claim(
                claim_id="popfreq.primary_label",
                rendered_text=str(card.get("primary_label") or ""),
                rendered_in="call_card.primary_label",
                claim_kind="population_frequency_band",
                claim_level="variant_specific" if has_frequency else "unsupported",
                verdict="supported" if has_frequency else "unverifiable",
                source_status=str(source_status),
                source_facts=_frequency_source_facts(detail),
                provenance=provenance,
                warnings=warnings,
            )
        )
        for badge in _dicts(card.get("support_badges")):
            code = _acmg_code(str(badge.get("text") or ""))
            if code in {"PM2", "BS1", "BA1"}:
                claims.append(
                    _evaluate_acmg_badge_claim(
                        claim_id=f"popfreq.{code.lower()}_badge",
                        rendered_text=str(badge.get("text") or ""),
                        rendered_in="call_card.support_badge",
                        claim_kind="acmg_frequency_code",
                        code=code,
                        payload=payload,
                        evidence_map=evidence_map,
                        statuses=statuses,
                        provenance=provenance,
                        extra_source_facts=_frequency_source_facts(detail),
                        extra_warnings=_frequency_code_warnings(code, detail),
                    )
                )
    elif detail:
        claims.append(
            _claim(
                claim_id="popfreq.detail",
                rendered_text="Population frequency detail",
                rendered_in="population_frequency_detail",
                claim_kind="population_frequency_detail",
                claim_level="variant_specific",
                verdict="supported",
                source_status=str(source_status),
                source_facts=_frequency_source_facts(detail),
                provenance=provenance,
                warnings=warnings,
            )
        )
    return _section("popfreq", "Population Frequency", str(source_status), claims)


def _publications_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    literature = _dict_or_empty(payload.get("publications_literature"))
    callout = _dict_or_empty(payload.get("publications_callout"))
    articles = _dicts(literature.get("articles") or payload.get("pubmed_articles"))
    status = _combined_status(statuses, ("litvar2", "pubmed"))
    claims: list[dict[str, Any]] = []
    total = literature.get("total_count", callout.get("total_count"))
    scope_counts = _dict_or_empty(literature.get("scope_counts") or callout.get("scope_counts"))
    claims.append(
        _claim(
            claim_id="publications.headline_count",
            rendered_text=f"{total or 0} publications",
            rendered_in="publications_callout.total_count",
            claim_kind="publication_count",
            claim_level="variant_specific" if total else "unsupported",
            verdict="supported" if total else "unverifiable",
            source_status=status,
            source_facts=[
                _fact("publications_literature", "total_count", total),
                _fact("publications_literature", "scope_counts", scope_counts),
            ],
            provenance=_publication_provenance(literature, evidence_map),
            warnings=_string_list(literature.get("warnings")),
        )
    )
    for article in articles:
        pmid = str(article.get("pmid") or "")
        snippet_status = str(article.get("snippet_status") or "")
        claim_level = _publication_claim_level(snippet_status)
        verdict = "supported" if claim_level == "variant_specific" else "downgraded"
        if claim_level == "unverifiable":
            verdict = "unverifiable"
        claims.append(
            _claim(
                claim_id=f"publications.pmid_{pmid or 'unknown'}",
                rendered_text=str(article.get("title") or pmid or "Publication"),
                rendered_in="publications.article",
                claim_kind="publication_article",
                claim_level=claim_level,
                verdict=verdict,
                source_status=status,
                source_facts=[
                    _fact("publication", "pmid", pmid),
                    _fact("publication", "snippet_status", snippet_status),
                    _fact("publication", "matched_terms", _article_matched_terms(article)),
                ],
                provenance=_dedupe([f"PMID:{pmid}"] if pmid else []),
                warnings=_string_list(article.get("warnings")),
            )
        )
    return _section("publications", "Publication Literature", status, claims)


def _trials_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    trials = _dict_or_empty((_profile(payload).get("therapies_trials")))
    if not trials:
        trials = _dict_or_empty(evidence_map.get("clinical_trials"))
    rows = _dicts(trials.get("trial_rows"))
    status = statuses.get("clinical_trials", "missing")
    query_term = _first_text(
        (
            _first_item(trials.get("provenance")).get("query", {}).get("query")
            if isinstance(_first_item(trials.get("provenance")).get("query"), dict)
            else None
        ),
        _dict_or_empty(evidence_map.get("clinical_trials")).get("query_term"),
    )
    claims = [_trial_claim(row, status=str(status), query_term=query_term) for row in rows]
    return _section("trials", "Clinical Trials", str(status), claims)


def _clinical_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    card = _card(payload, "clinical_consensus")
    consensus = _dict_or_empty(evidence_map.get("clinical_consensus"))
    worksheet = _worksheet(payload, evidence_map)
    status = (
        statuses.get("clinical_consensus")
        or statuses.get("clingen")
        or statuses.get("clinvar", "missing")
    )
    claims: list[dict[str, Any]] = []
    if card:
        claims.append(
            _claim(
                claim_id="clinical.primary_label",
                rendered_text=str(card.get("primary_label") or ""),
                rendered_in="call_card.primary_label",
                claim_kind="clinical_consensus_classification",
                claim_level="variant_specific",
                verdict="supported" if worksheet or consensus else "unverifiable",
                source_status=str(status),
                source_facts=[
                    _fact("clinical_consensus", "classification", consensus.get("classification")),
                    _fact(
                        "clinical_consensus",
                        "classification_source",
                        consensus.get("classification_source"),
                    ),
                ],
                provenance=_string_list(card.get("provenance")),
                warnings=_string_list(card.get("warnings")),
            )
        )
    return _section("clinical", "Clinical Consensus", str(status), claims)


def _acmg_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    status = (
        statuses.get("clinical_consensus")
        or statuses.get("clingen")
        or statuses.get("clinvar", "missing")
    )
    claims = []
    for row in _worksheet_criteria(payload, evidence_map):
        code = str(row.get("code") or "")
        claims.append(
            _claim(
                claim_id=f"acmg.{code.lower() or 'unknown'}",
                rendered_text=str(row.get("applied_strength") or row.get("strength") or code),
                rendered_in="report_profile.acmg_worksheet.criteria",
                claim_kind="acmg_worksheet_criterion",
                claim_level="variant_specific" if row.get("state") == "met" else "unsupported",
                verdict="supported" if row.get("state") == "met" else "unverifiable",
                source_status=str(status),
                source_facts=[_criterion_fact(row)],
                provenance=_string_list(row.get("evidence_refs")),
                warnings=_string_list(row.get("warnings")),
            )
        )
    return _section("acmg", "ACMG Worksheet", str(status), claims)


def _disease_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    disease = _dict_or_empty(_profile(payload).get("disease_mechanism"))
    status = statuses.get("gene_disease", "missing")
    has_condition = bool(disease.get("primary_condition") or disease.get("disease_ids"))
    claims = [
        _claim(
            claim_id="disease.primary_condition",
            rendered_text=str(disease.get("primary_condition") or "No disease resolved"),
            rendered_in="report_profile.disease_mechanism",
            claim_kind="disease_mechanism",
            claim_level="disease_level" if has_condition else "unsupported",
            verdict="supported" if has_condition else "unverifiable",
            source_status=str(status),
            source_facts=[
                _fact("disease_mechanism", "primary_condition", disease.get("primary_condition")),
                _fact("disease_mechanism", "disease_ids", disease.get("disease_ids")),
            ],
            provenance=_provenance_from_objects(disease.get("provenance")),
            warnings=_string_list(disease.get("warnings")),
        )
    ]
    return _section("disease", "Disease Mechanism", str(status), claims)


def _gene_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    gene = _dict_or_empty(_profile(payload).get("gene_context_snapshot"))
    status = str(gene.get("source_status") or statuses.get("gene_context_snapshot", "missing"))
    has_gene_fact = any(gene.get(key) is not None for key in ("ensembl_gene_id", "gene_length"))
    claims = [
        _claim(
            claim_id="gene.context_snapshot",
            rendered_text=str(gene.get("gene") or "Gene context unavailable"),
            rendered_in="report_profile.gene_context_snapshot",
            claim_kind="gene_context",
            claim_level="gene_level" if has_gene_fact else "unsupported",
            verdict="supported" if has_gene_fact else "unverifiable",
            source_status=status,
            source_facts=[
                _fact("gene_context_snapshot", "ensembl_gene_id", gene.get("ensembl_gene_id")),
                _fact("gene_context_snapshot", "gene_length", gene.get("gene_length")),
            ],
            provenance=_provenance_from_objects(gene.get("provenance")),
            warnings=_string_list(gene.get("warnings")),
        )
    ]
    return _section("gene", "Gene Context", status, claims)


def _protein_section(
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    profile = _profile(payload)
    molecular = _dict_or_empty(profile.get("molecular_context"))
    gene_snapshot = _dict_or_empty(profile.get("gene_context_snapshot"))
    gene_variant = _dict_or_empty(gene_snapshot.get("variant"))
    row = _first_item(payload.get("variant_summary_rows"))
    header = _dict_or_empty(profile.get("header"))
    surfaced = _first_text(
        row.get("protein_change"),
        header.get("protein_change"),
        gene_variant.get("hgvs_p"),
    )
    derived = _derive_protein_change(
        molecular.get("protein_position"),
        molecular.get("codon_change"),
    )
    status = statuses.get("molecular_context", "missing")
    warnings = _string_list(molecular.get("warnings"))
    if derived and not surfaced:
        warnings = _dedupe([*warnings, "protein_change_derivable_not_surfaced"])
        verdict = "contradicted"
        claim_level = "unsupported"
        rendered_text = "protein_change omitted"
    elif surfaced:
        verdict = "supported"
        claim_level = "variant_specific"
        rendered_text = surfaced
    else:
        verdict = "unverifiable"
        claim_level = "unsupported"
        rendered_text = "protein_change unavailable"
    claims = [
        _claim(
            claim_id="protein.protein_change",
            rendered_text=rendered_text,
            rendered_in="variant_summary_rows[0].protein_change",
            claim_kind="protein_change_surface",
            claim_level=claim_level,
            verdict=verdict,
            source_status=str(status),
            source_facts=[
                _fact("molecular_context", "protein_position", molecular.get("protein_position")),
                _fact("molecular_context", "codon_change", molecular.get("codon_change")),
                _fact("derived", "protein_change", derived),
                _fact("variant_summary_rows[0]", "protein_change", row.get("protein_change")),
                _fact("report_profile.header", "protein_change", header.get("protein_change")),
                _fact("gene_context_snapshot.variant", "hgvs_p", gene_variant.get("hgvs_p")),
            ],
            provenance=_provenance_from_objects(molecular.get("provenance")),
            warnings=warnings,
        )
    ]
    return _section("protein", "Protein Context", str(status), claims)


def _evaluate_acmg_badge_claim(
    *,
    claim_id: str,
    rendered_text: str,
    rendered_in: str,
    claim_kind: str,
    code: str,
    payload: dict[str, Any],
    evidence_map: dict[str, Any],
    statuses: Mapping[str, str],
    provenance: Sequence[str] | None = None,
    extra_source_facts: Sequence[Mapping[str, Any]] | None = None,
    extra_warnings: Sequence[str] | None = None,
) -> dict[str, Any]:
    criteria = _worksheet_criteria(payload, evidence_map)
    matching = [row for row in criteria if row.get("code") == code and row.get("state") == "met"]
    opposing = [
        row
        for row in criteria
        if row.get("code") in _ACMG_AXIS_OPPOSITES.get(code, set()) and row.get("state") == "met"
    ]
    source_facts: list[Mapping[str, Any]] = []
    source_facts.extend(_criterion_fact(row) for row in matching)
    source_facts.extend(_criterion_fact(row) for row in opposing)
    source_facts.extend(extra_source_facts or [])
    warnings = list(extra_warnings or [])
    if opposing:
        verdict = "contradicted"
        claim_level = "unsupported"
        warnings.append(
            "pill_claim_contradicts_source:"
            + f"{code}_vs_{'/'.join(str(row.get('code')) for row in opposing)}"
        )
    elif matching:
        verdict = "supported"
        claim_level = "variant_specific"
        if any(row.get("assertion_level") == "eamos_hint" for row in matching):
            warnings.append("claim_source:eamos_hint")
    else:
        verdict = "unsupported"
        claim_level = "unsupported"
        warnings.append(f"badge_not_in_worksheet:{code}")

    status = (
        statuses.get("clinical_consensus")
        or statuses.get("clingen")
        or statuses.get("clinvar", "missing")
    )
    return _claim(
        claim_id=claim_id,
        rendered_text=rendered_text,
        rendered_in=rendered_in,
        claim_kind=claim_kind,
        claim_level=claim_level,
        verdict=verdict,
        source_status=str(status),
        source_facts=source_facts,
        provenance=provenance or [],
        warnings=warnings,
    )


def _metric_badge_claim(
    *,
    card_id: str,
    text: str,
    badge: Mapping[str, Any],
    card: Mapping[str, Any],
    payload: dict[str, Any],
    statuses: Mapping[str, str],
) -> dict[str, Any]:
    source_status = _source_status_for_card(card, statuses)
    facts: list[Mapping[str, Any]] = []
    verdict = "supported"
    claim_level = "variant_specific"
    if card_id == "population_frequency":
        detail = _dict_or_empty(payload.get("population_frequency_detail"))
        facts = _frequency_source_facts(detail)
        if text.startswith("AC ") and str(detail.get("allele_count")) not in text:
            verdict = "unsupported"
            claim_level = "unsupported"
    elif badge.get("kind") in {"neutral", "warning"} and text in {"None", "gnomAD unavailable"}:
        verdict = "unverifiable"
        claim_level = "unsupported"
    return _claim(
        claim_id=f"pills.{card_id}.{_slug(text)}",
        rendered_text=text,
        rendered_in="call_card.support_badge",
        claim_kind="metric_badge",
        claim_level=claim_level,
        verdict=verdict,
        source_status=source_status,
        source_facts=facts,
        provenance=_string_list(card.get("provenance")),
        warnings=_string_list(card.get("warnings")),
    )


def _trial_claim(row: Mapping[str, Any], *, status: str, query_term: str | None) -> dict[str, Any]:
    nct_id = str(row.get("nct_id") or "unknown")
    matched_terms = _string_list(row.get("matched_terms"))
    match_level = str(row.get("match_level") or "unavailable")
    warnings = _string_list(row.get("warnings"))
    if not matched_terms:
        claim_level = "unsupported"
        verdict = "unsupported"
        warnings = _dedupe([*warnings, "match_without_matched_terms"])
    elif match_level == "variant_level":
        claim_level = "variant_specific"
        verdict = "supported"
    elif match_level in {"gene_level", "disease_level"}:
        claim_level = match_level
        verdict = "downgraded"
    else:
        claim_level = "unsupported"
        verdict = "unverifiable"
    provenance = [item for item in [nct_id, str(row.get("source_url") or "")] if item]
    return _claim(
        claim_id=f"trials.{nct_id}",
        rendered_text=" ".join(
            item for item in [nct_id, str(row.get("title") or "")] if item
        ).strip(),
        rendered_in="report_profile.therapies_trials.trial_rows",
        claim_kind="clinical_trial_row",
        claim_level=claim_level,
        verdict=verdict,
        source_status=status,
        source_facts=[
            _fact("ClinicalTrials.gov", "nct_id", nct_id),
            _fact("ClinicalTrials.gov", "match_level", match_level),
            _fact("ClinicalTrials.gov", "matched_terms", matched_terms),
            _fact("ClinicalTrials.gov", "query_term", query_term),
        ],
        provenance=provenance,
        warnings=warnings,
    )


def _claim(
    *,
    claim_id: str,
    rendered_text: str,
    rendered_in: str,
    claim_kind: str,
    claim_level: str,
    verdict: str,
    source_status: str,
    source_facts: Sequence[Mapping[str, Any]] | None = None,
    provenance: Sequence[str] | None = None,
    warnings: Sequence[str] | None = None,
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "rendered_text": rendered_text,
        "rendered_in": rendered_in,
        "claim_kind": claim_kind,
        "claim_level": claim_level,
        "verdict": verdict,
        "source_status": source_status or "missing",
        "source_facts": [dict(fact) for fact in (source_facts or [])],
        "provenance": _dedupe(str(item) for item in (provenance or []) if item),
        "warnings": _dedupe(str(item) for item in (warnings or []) if item),
    }


def _section(
    section: str,
    title: str,
    source_status: str,
    claims: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "section": section,
        "title": title,
        "source_status": source_status or "missing",
        "claims": [dict(claim) for claim in claims],
    }


def _summary(claims: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    summary = {
        "claims_total": len(claims),
        "variant_specific": 0,
        "gene_level": 0,
        "disease_level": 0,
        "unsupported": 0,
        "supported": 0,
        "downgraded": 0,
        "contradicted": 0,
        "unverifiable": 0,
    }
    for claim in claims:
        level = str(claim.get("claim_level") or "")
        verdict = str(claim.get("verdict") or "")
        if level in {"variant_specific", "gene_level", "disease_level"}:
            summary[level] += 1
        if verdict in {"supported", "downgraded", "unsupported", "contradicted", "unverifiable"}:
            summary[verdict] += 1
    return summary


def _normalize_sections(sections: Sequence[str] | str | None) -> tuple[str, ...]:
    if sections is None:
        return DEFAULT_SECTIONS
    if isinstance(sections, str):
        raw = [item.strip() for item in sections.split(",")]
    else:
        raw = [str(item).strip() for item in sections]
    if any(item == "all" for item in raw):
        return SECTION_ORDER
    normalized = tuple(item for item in raw if item in SECTION_ORDER)
    return normalized or DEFAULT_SECTIONS


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _jsonish(item) for key, item in value.items()}
    return {}


def _jsonish(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _jsonish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonish(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonish(item) for item in value]
    return value


def _profile(payload: Mapping[str, Any]) -> dict[str, Any]:
    return _dict_or_empty(payload.get("report_profile"))


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _first_item(value: Any) -> dict[str, Any]:
    values = _dicts(value)
    return values[0] if values else {}


def _card(payload: Mapping[str, Any], card_id: str) -> dict[str, Any]:
    cards = _dicts(_dict_or_empty(payload.get("call_cards")).get("cards"))
    return next((card for card in cards if card.get("card_id") == card_id), {})


def _worksheet(payload: Mapping[str, Any], evidence_map: Mapping[str, Any]) -> dict[str, Any]:
    consensus = _dict_or_empty(evidence_map.get("clinical_consensus"))
    worksheet = _dict_or_empty(consensus.get("acmg_worksheet"))
    if worksheet:
        return worksheet
    return _dict_or_empty(_profile(payload).get("acmg_worksheet"))


def _worksheet_criteria(
    payload: Mapping[str, Any],
    evidence_map: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return _dicts(_worksheet(payload, evidence_map).get("criteria"))


def _criterion_fact(row: Mapping[str, Any]) -> dict[str, Any]:
    code = row.get("code")
    return _fact(
        "acmg_worksheet",
        f"{code}.state" if code else "criterion.state",
        row.get("state"),
        assertion_level=row.get("assertion_level"),
        criterion_source=row.get("source"),
        note=row.get("rationale"),
    )


def _fact(source: str, field: str, value: Any, **extra: Any) -> dict[str, Any]:
    fact = {"source": source, "field": field, "value": value}
    for key, item in extra.items():
        if item is not None:
            fact[key] = item
    return fact


def _frequency_source_facts(detail: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not detail:
        return []
    return [
        _fact("gnomAD", "variant_id", detail.get("variant_id")),
        _fact("gnomAD", "allele_frequency", detail.get("allele_frequency")),
        _fact("gnomAD", "popmax_frequency", detail.get("popmax_frequency")),
        _fact("gnomAD", "popmax_population", detail.get("popmax_population")),
        _fact("gnomAD", "allele_count", detail.get("allele_count")),
        _fact("gnomAD", "allele_number", detail.get("allele_number")),
        _fact("gnomAD", "homozygote_count", detail.get("homozygote_count")),
    ]


def _frequency_code_warnings(code: str, detail: Mapping[str, Any]) -> list[str]:
    warnings = []
    hom = _as_int(detail.get("homozygote_count"))
    if code == "PM2" and hom is not None and hom > 0:
        warnings.append("rarity_code_with_homozygotes")
    return warnings


def _population_band_warnings(detail: Mapping[str, Any]) -> list[str]:
    popmax = _as_float(detail.get("popmax_frequency"))
    group_afs = [
        _as_float(item.get("allele_frequency"))
        for item in _dicts(detail.get("genetic_ancestry_groups"))
    ]
    group_afs = [item for item in group_afs if item is not None]
    if popmax is not None and group_afs and max(group_afs) > popmax:
        return ["band_max_af_understated"]
    return []


def _acmg_code(text: str) -> str | None:
    candidate = text.strip().split()[0] if text.strip() else ""
    match = _ACMG_CODE_RE.match(candidate)
    return match.group(1) if match else None


def _publication_claim_level(snippet_status: str) -> str:
    if snippet_status == "exact_variant_snippet":
        return "variant_specific"
    if snippet_status == "gene_only_no_variant":
        return "gene_level"
    if snippet_status:
        return "unverifiable"
    return "unsupported"


def _article_matched_terms(article: Mapping[str, Any]) -> list[str]:
    terms: list[str] = []
    for snippet in _dicts(article.get("snippets")):
        terms.extend(_string_list(snippet.get("matched_terms")))
    return _dedupe(terms)


def _publication_provenance(
    literature: Mapping[str, Any],
    evidence_map: Mapping[str, Any],
) -> list[str]:
    provenance = []
    query = _dict_or_empty(_dict_or_empty(literature.get("scope_counts")).get("variant")).get(
        "query"
    ) or _dict_or_empty(evidence_map.get("pubmed")).get("query")
    if query:
        provenance.append(f"query:{query}")
    return provenance


def _provenance_from_objects(value: Any) -> list[str]:
    provenance = []
    for item in _dicts(value):
        source = item.get("source")
        url = item.get("source_url")
        query = item.get("query")
        if source:
            provenance.append(str(source))
        if url:
            provenance.append(str(url))
        if isinstance(query, dict) and query:
            provenance.append("query:" + ",".join(f"{key}={val}" for key, val in query.items()))
    return _dedupe(provenance)


def _source_urls(value: Mapping[str, Any]) -> list[str]:
    return [str(value["source_url"])] if value.get("source_url") else []


def _source_status_for_card(card: Mapping[str, Any], statuses: Mapping[str, str]) -> str:
    status = card.get("source_status")
    if status:
        return str(status)
    card_id = card.get("card_id")
    if card_id == "population_frequency":
        return statuses.get("gnomad", "missing")
    if card_id == "clinical_consensus":
        return (
            statuses.get("clinical_consensus")
            or statuses.get("clingen")
            or statuses.get("clinvar", "missing")
        )
    if card_id == "lab_functional":
        return _combined_status(statuses, ("clingen", "clinvar", "pubmed"))
    if card_id == "computational":
        return _combined_status(statuses, ("computational_annotations", "spliceai", "vep"))
    return "missing"


def _combined_status(statuses: Mapping[str, str], sources: Sequence[str]) -> str:
    values = [statuses.get(source) for source in sources if statuses.get(source)]
    if not values:
        return "missing"
    order = ["live", "cache", "stale", "fixture", "fallback", "degraded", "error", "failed"]
    for status in order:
        if status in values:
            return status
    return values[0] or "missing"


def _derive_protein_change(position: Any, codon_change: Any) -> str | None:
    if position is None or not codon_change:
        return None
    match = re.match(r"^([ACGTU]{3})>([ACGTU]{3})$", str(codon_change).upper())
    if not match:
        return None
    ref = match.group(1).replace("U", "T")
    alt = match.group(2).replace("U", "T")
    ref_aa = _CODON_TO_AA3.get(ref)
    alt_aa = _CODON_TO_AA3.get(alt)
    if not ref_aa or not alt_aa:
        return None
    return f"p.{ref_aa}{position}{alt_aa}"


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None and str(item)]


def _dedupe(values: Sequence[str] | Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "badge"


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
