from __future__ import annotations

from app.tools.clinical_trials import ClinicalTrialsTool
from app.tools.clinvar import ClinvarTool
from app.tools.ensembl_vep import EnsemblVepTool
from app.tools.gnomad import GnomadTool
from app.tools.pubmed import PubmedTool
from app.tools.spliceai import SpliceAiTool


def build_tool_registry(settings):
    return {
        "clinvar": ClinvarTool(settings),
        "vep": EnsemblVepTool(settings),
        "spliceai": SpliceAiTool(settings),
        "gnomad": GnomadTool(settings),
        "pubmed": PubmedTool(settings),
        "clinical_trials": ClinicalTrialsTool(settings),
    }
