from __future__ import annotations

from app.tools.clinical_trials import ClinicalTrialsTool
from app.tools.clinvar import ClinvarTool
from app.tools.ensembl_vep import EnsemblVepTool
from app.tools.gnomad import GnomadTool
from app.tools.litvar2 import LitVar2Tool
from app.tools.pubmed import PubmedTool
from app.tools.spliceai import SpliceAiTool
from app.tools.variant_validator import VariantValidatorTool

STRICT_GENOMIC_PLUGINS = ("gnomad", "spliceai")
"""FixtureBackedTool names whose get_evidence reads variant.genomic_hg38.

Strict-genomic plugins should degrade to a live_stub or fixture result if
coordinates are absent rather than resolving transcript HGVS themselves.
"""


def build_tool_registry(settings):
    return {
        "clinvar": ClinvarTool(settings),
        "vep": EnsemblVepTool(settings),
        "variant_validator": VariantValidatorTool(settings),
        "spliceai": SpliceAiTool(settings),
        "gnomad": GnomadTool(settings),
        "pubmed": PubmedTool(settings),
        "litvar2": LitVar2Tool(settings),
        "clinical_trials": ClinicalTrialsTool(settings),
    }
