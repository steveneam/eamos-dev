from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha1

from app.schemas.capabilities import CapabilityExecutionDisclosureV2
from app.schemas.panels import (
    Panel,
    PanelGene,
    PanelListResponse,
    PanelResolveRequest,
    PanelSourceSnapshotV2,
    PanelSummary,
)

LOCAL_PANEL_VERSION = "2026-06-04-local-launch-v1"
LOCAL_PANEL_WARNING = (
    "local launch catalog; external PanelApp/ClinGen/GenCC materialized source pending"
)
LOCAL_PANEL_REQUIREMENTS = (
    "materialize version-pinned HGNC, MANE, GenCC, and Mondo artifacts",
    "build and verify the immutable panel/interval manifest",
    "pass the panel resolution and interval functional probes",
)
PANELAPP_GEL_LAUNCH_GATE = (
    "PanelApp GEL remains disabled pending explicit downstream-use rights approval."
)
_LOCAL_RELEASE_DATE = datetime(2026, 6, 4, tzinfo=UTC)


class PanelService:
    def __init__(self, *, source_panels: list[Panel] | None = None) -> None:
        self._panels = [
            panel.model_copy(deep=True)
            for panel in (source_panels if source_panels is not None else _launch_panels())
        ]
        self._gene_index = _gene_index(self._panels)

    def list_panels(self) -> PanelListResponse:
        return PanelListResponse(panels=[_summary(panel) for panel in self._panels])

    def get_panel(self, slug: str) -> Panel | None:
        normalized = _slug(slug)
        for panel in self._panels:
            if panel.slug == normalized:
                return panel.model_copy(deep=True)
        return None

    def resolve(self, request: PanelResolveRequest) -> Panel:
        if request.symbols:
            return self._resolve_symbols(request.symbols)
        if request.disease_mondo:
            return self._resolve_disease(request.disease_mondo)
        return self._resolve_upload_ref(request.upload_ref or "")

    def _resolve_symbols(self, symbols: list[str]) -> Panel:
        genes: list[PanelGene] = []
        for symbol in symbols:
            indexed = self._gene_index.get(symbol)
            if indexed is None:
                genes.append(
                    PanelGene(
                        symbol=symbol,
                        confidence=None,
                        provenance=["submitted_symbol"],
                        warnings=["symbol_not_in_local_launch_catalog"],
                    )
                )
            else:
                genes.append(indexed.model_copy(deep=True))

        slug = f"custom-symbols-{_stable_panel_hash([gene.symbol for gene in genes])}"
        return Panel(
            id=slug,
            name=f"Custom symbol panel ({len(genes)} genes)",
            slug=slug,
            source="custom",
            version=LOCAL_PANEL_VERSION,
            provenance_url=None,
            genes=genes,
            intervals_ref="hg38",
            source_snapshot_v2=_unavailable_custom_snapshot(
                snapshot_key=slug,
                claim="HGNC-normalized custom symbol panel",
            ),
            warnings=[
                "resolved from submitted symbols",
                "HGNC alias normalization is pending materialized HGNC data",
            ],
        )

    def _resolve_disease(self, disease_mondo: str) -> Panel:
        query = disease_mondo.strip().upper()
        if query in {"MONDO:0019200", "MONDO:0021122"}:
            panel = self.get_panel("inherited-retinal-disease")
            if panel is not None:
                panel.warnings.append("resolved by local MONDO seed mapping")
                return panel
        slug = f"custom-disease-{_stable_panel_hash([query])}"
        return Panel(
            id=slug,
            name=f"Disease panel {query}",
            slug=slug,
            source="custom",
            version=LOCAL_PANEL_VERSION,
            genes=[],
            intervals_ref="hg38",
            source_snapshot_v2=_unavailable_custom_snapshot(
                snapshot_key=slug,
                claim="Mondo and GenCC disease-to-gene panel resolution",
            ),
            warnings=[
                "disease_mondo_resolution_pending_materialized_mondo_gencc_sources",
            ],
        )

    def _resolve_upload_ref(self, upload_ref: str) -> Panel:
        slug = f"custom-upload-{_stable_panel_hash([upload_ref])}"
        return Panel(
            id=slug,
            name="Uploaded gene panel",
            slug=slug,
            source="custom",
            version=LOCAL_PANEL_VERSION,
            genes=[],
            intervals_ref="hg38",
            source_snapshot_v2=_unavailable_custom_snapshot(
                snapshot_key=slug,
                claim="Owner-scoped uploaded gene panel resolution",
            ),
            warnings=["upload_ref_panel_resolution_pending_batch_upload_store"],
        )


def _launch_panels() -> list[Panel]:
    panels = [
        _panel(
            name="Inherited retinal disease",
            slug="inherited-retinal-disease",
            genes=[
                _gene("ABCA4", "HGNC:34", "AR"),
                _gene("USH2A", "HGNC:12601", "AR"),
                _gene("RPE65", "HGNC:10294", "AR"),
                _gene("RPGR", "HGNC:10295", "XL"),
                _gene("CRB1", "HGNC:2343", "AR"),
                _gene("RHO", "HGNC:10012", "AD"),
                _gene("EYS", "HGNC:21555", "AR"),
                _gene("CEP290", "HGNC:29021", "AR"),
                _gene("PRPH2", "HGNC:9942", "AD"),
                _gene("BEST1", "HGNC:1242", "AD", confidence="amber"),
                _gene("CHM", "HGNC:1894", "XL"),
                _gene("RP1", "HGNC:10263", "AD", confidence="amber"),
            ],
        ),
        _panel(
            name="Cardiomyopathy & arrhythmia",
            slug="cardiomyopathy-arrhythmia",
            genes=[
                _gene("MYH7", "HGNC:7577", "AD"),
                _gene("MYBPC3", "HGNC:7551", "AD"),
                _gene("TNNT2", "HGNC:11949", "AD"),
                _gene("TNNI3", "HGNC:11947", "AD"),
                _gene("TPM1", "HGNC:12010", "AD", confidence="amber"),
                _gene("SCN5A", "HGNC:10593", "AD"),
                _gene("KCNQ1", "HGNC:6294", "AD"),
                _gene("KCNH2", "HGNC:6251", "AD"),
                _gene("LMNA", "HGNC:6636", "AD"),
                _gene("PKP2", "HGNC:9024", "AD"),
                _gene("DSP", "HGNC:3052", "AD", confidence="amber"),
            ],
        ),
        _panel(
            name="Hereditary cancer (core)",
            slug="hereditary-cancer",
            genes=[
                _gene("BRCA1", "HGNC:1100", "AD"),
                _gene("BRCA2", "HGNC:1101", "AD"),
                _gene("TP53", "HGNC:11998", "AD"),
                _gene("PALB2", "HGNC:26144", "AD"),
                _gene("ATM", "HGNC:795", "AD", confidence="amber"),
                _gene("CHEK2", "HGNC:16627", "AD", confidence="amber"),
                _gene("MLH1", "HGNC:7127", "AD"),
                _gene("MSH2", "HGNC:7325", "AD"),
                _gene("MSH6", "HGNC:7329", "AD"),
                _gene("PMS2", "HGNC:9122", "AD"),
                _gene("APC", "HGNC:583", "AD"),
            ],
        ),
        _panel(
            name="Project-100 hardening panel",
            slug="project-100-hardening",
            genes=[
                _gene("ABCA4", "HGNC:34", None),
                _gene("APC", "HGNC:583", None),
                _gene("BRCA1", "HGNC:1100", None),
                _gene("BRCA2", "HGNC:1101", None),
                _gene("CFTR", "HGNC:1884", None),
                _gene("HBB", "HGNC:4827", None),
                _gene("LDLR", "HGNC:6547", None),
                _gene("MLH1", "HGNC:7127", None),
                _gene("PAH", "HGNC:8582", None),
                _gene("TP53", "HGNC:11998", None),
            ],
            warnings=[
                LOCAL_PANEL_WARNING,
                "derived from project_100_sample_manifest for batch validation",
            ],
        ),
    ]
    return [panel.model_copy(deep=True) for panel in panels]


def _panel(
    *,
    name: str,
    slug: str,
    genes: list[PanelGene],
    warnings: list[str] | None = None,
) -> Panel:
    panel = Panel(
        id=f"local-{slug}",
        name=name,
        slug=slug,
        source="custom",
        version=LOCAL_PANEL_VERSION,
        provenance_url=None,
        genes=deepcopy(genes),
        intervals_ref="hg38",
        source_snapshot_v2=_unavailable_custom_snapshot(
            snapshot_key=slug,
            claim=f"Source-backed {name} panel catalog",
        ),
        warnings=warnings or [LOCAL_PANEL_WARNING],
    )
    return panel


def _gene(
    symbol: str,
    hgnc_id: str,
    moi: str | None,
    *,
    confidence: str = "green",
) -> PanelGene:
    return PanelGene(
        symbol=symbol,
        hgnc_id=hgnc_id,
        confidence=confidence,
        moi=moi,
        provenance=["local_launch_catalog"],
        warnings=[],
    )


def _summary(panel: Panel) -> PanelSummary:
    return PanelSummary(
        id=panel.id,
        name=panel.name,
        slug=panel.slug,
        source=panel.source,
        version=panel.version,
        provenance_url=panel.provenance_url,
        source_snapshot_v2=panel.source_snapshot_v2,
        gene_count=len(panel.genes),
        intervals_ref=panel.intervals_ref,
        warnings=list(panel.warnings),
    )


def _gene_index(panels: list[Panel]) -> dict[str, PanelGene]:
    index: dict[str, PanelGene] = {}
    for panel in panels:
        for gene in panel.genes:
            index.setdefault(gene.symbol, gene.model_copy(deep=True))
    return index


def _stable_panel_hash(values: list[str]) -> str:
    normalized = ",".join(value.strip().upper() for value in values if value.strip())
    return sha1(normalized.encode("utf-8")).hexdigest()[:10]


def _slug(value: str) -> str:
    return value.strip().lower()


def _unavailable_custom_snapshot(*, snapshot_key: str, claim: str) -> PanelSourceSnapshotV2:
    snapshot_id = f"panel-custom-{_stable_panel_hash([snapshot_key])}"
    disclosure = CapabilityExecutionDisclosureV2(
        capability_id=f"panel.catalog.{_stable_panel_hash([snapshot_key, claim])}",
        claim=claim,
        execution="unavailable",
        input_scope="grch38_gene_panel",
        source_status="unavailable",
        source_release=LOCAL_PANEL_VERSION,
        applicability="applicable",
        validation_status="unvalidated",
        retention="none",
        consent_required=False,
        warnings=[LOCAL_PANEL_WARNING, PANELAPP_GEL_LAUNCH_GATE],
        requirements=list(LOCAL_PANEL_REQUIREMENTS),
    )
    return PanelSourceSnapshotV2(
        snapshot_id=snapshot_id,
        source="custom",
        version=LOCAL_PANEL_VERSION,
        release=LOCAL_PANEL_VERSION,
        retrieved_at=_LOCAL_RELEASE_DATE,
        launch_posture="unavailable",
        licence_id="Eamos-internal-custom-seed",
        provenance_url=None,
        artifact_manifest_id=None,
        artifact_sha256=None,
        execution_disclosure=disclosure,
    )
