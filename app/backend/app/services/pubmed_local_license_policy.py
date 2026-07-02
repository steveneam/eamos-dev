from __future__ import annotations

from app.services.pubmed_local_constants import PERMISSIVE_LICENSE_PROFILES


def _normalize_space(value: str) -> str:
    return " ".join(value.split())


def classify_license_profile(value: str | None) -> str:
    text = _normalize_space(value or "").lower()
    if not text:
        return "unknown"
    if any(token in text for token in ("no-cc", "no cc", "no machine-readable")):
        return "unknown"
    if any(token in text for token in ("noncommercial", "non-commercial", "cc by-nc", "cc-by-nc")):
        return "noncommercial"
    if any(token in text for token in ("no derivatives", "no-derivatives", "cc by-nd", "cc-by-nd")):
        return "no_derivatives"
    if "cc0" in text or "creative commons zero" in text:
        return "cc0"
    if "public domain" in text or text in {"pd", "pdm"}:
        return "public_domain"
    if "u.s. government" in text or "us government" in text:
        return "us_government"
    if (
        "cc by-sa" in text
        or "cc-by-sa" in text
        or "creative commons attribution-sharealike" in text
    ):
        return "cc_by_sa"
    if "cc by" in text or "cc-by" in text or "creative commons attribution" in text:
        return "cc_by"
    if "copyright" in text or "©" in text:
        return "publisher_copyright"
    return "unknown"


def abstract_policy_for_license(license_profile: str, abstract_text: str | None) -> str:
    if not abstract_text:
        return "metadata_only_no_abstract"
    if license_profile in PERMISSIVE_LICENSE_PROFILES:
        return "licensed_text_persisted"
    return "metadata_only_license_unverified"
