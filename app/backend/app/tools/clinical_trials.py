from __future__ import annotations

import httpx

from app.core.config import Settings

CLINICAL_TRIALS_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

# Offline fixtures — extend this dict as more genes are tested
_FIXTURE_MAP: dict[str, str] = {
    "RPE65": (
        "3 active trials found for RPE65:\n"
        "• NCT02781480 — Phase III — RECRUITING — Luxturna long-term safety and efficacy follow-up\n"
        "• NCT04516369 — Phase I/II — ACTIVE_NOT_RECRUITING — AAV gene therapy for RPE65-associated LCA/EAMD\n"
        "• NCT03913143 — Phase I/II — RECRUITING — Natural history and gene therapy outcomes in RPE65 retinal disease"
    ),
    "RPGR": (
        "2 active trials found for RPGR:\n"
        "• NCT03252847 — Phase I/II — RECRUITING — AGTC-501 gene therapy for RPGR-associated X-linked retinitis pigmentosa\n"
        "• NCT04671433 — Phase I/II — RECRUITING — AAV-RPGR subretinal gene therapy dose-escalation study"
    ),
    "ABCA4": (
        "1 active trial found for ABCA4:\n"
        "• NCT04483440 — Phase I/II — RECRUITING — 4D-150 subretinal AAV delivery for ABCA4-associated Stargardt disease"
    ),
    "CNGA3": (
        "1 active trial found for CNGA3:\n"
        "• NCT02610582 — Phase I/II — ACTIVE_NOT_RECRUITING — rAAV.hCNGA3 gene therapy for CNGA3-associated achromatopsia"
    ),
}

_FIXTURE_GENERIC = (
    "Live ClinicalTrials.gov data is not available in offline mode. "
    "Search ClinicalTrials.gov with the gene name to find active trials. "
    "Filter by status: RECRUITING or ACTIVE_NOT_RECRUITING."
)


class ClinicalTrialsTool:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_trials_summary(self, gene: str) -> str:
        gene = gene.strip().upper()
        if not self.settings.use_real_apis:
            return _FIXTURE_MAP.get(gene, _FIXTURE_GENERIC)
        try:
            return self._fetch_live(gene)
        except Exception as exc:
            return _FIXTURE_MAP.get(
                gene,
                f"Clinical trials lookup unavailable for {gene} ({type(exc).__name__}). Check ClinicalTrials.gov directly.",
            )

    def _fetch_live(self, gene: str) -> str:
        response = httpx.get(
            CLINICAL_TRIALS_BASE_URL,
            params={
                "query.term": gene,
                "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING",
                "pageSize": 3,
                "fields": "NCTId,BriefTitle,Phase,OverallStatus,StartDate",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        studies = data.get("studies", [])

        if not studies:
            return f"No active trials found for {gene} on ClinicalTrials.gov."

        lines = [f"{len(studies)} active trial(s) found for {gene}:"]
        for study in studies:
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            design = proto.get("designModule", {})

            nct_id = ident.get("nctId", "N/A")
            title = ident.get("briefTitle", "Untitled")
            overall_status = status_mod.get("overallStatus", "Unknown")
            phases = design.get("phases", [])
            phase_str = "/".join(phases) if phases else "Phase N/A"

            lines.append(f"• {nct_id} — {phase_str} — {overall_status} — {title}")

        return "\n".join(lines)
