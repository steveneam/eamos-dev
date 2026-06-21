from __future__ import annotations

import json
from hashlib import md5, sha256
from pathlib import Path

import pytest

from app.cli.eamos_uniprot_feature_index import main as uniprot_feature_index_main
from app.core.config import Settings
from app.data_sources.protein_assets import (
    ProteinAssetSpec,
    ProteinAssetStatus,
    inspect_protein_annotation_asset,
)
from app.data_sources.registry import DEFAULT_DATA_SOURCE_REGISTRY
from app.schemas.gene_viewer import ProteinFeatures
from app.schemas.protein_annotation import ProteinAnnotationRequest, ProteinDomainTrack
from app.services.protein_annotation import (
    HmmerRuntimeStatus,
    ProteinAnnotationService,
    UniProtFlatfileFeatureProvider,
    normalize_protein_input,
    parse_hmmer_domtblout,
    parse_uniprot_flatfile_features,
    protein_features_from_domain_track,
    write_uniprot_feature_index,
)

DOMTBLOUT = (
    "# hmmscan test fixture\n"
    "PF00001 PF00001.1 100 query - 600 1e-20 80.0 0.0 1 1 "
    "1e-22 1e-20 75.0 0.0 2 90 12 95 10 99 0.95 "
    "Reference control domain\n"
)
RPE65_DOMTBLOUT = (
    "# hmmscan RPE65 test fixture\n"
    "PF03055 PF03055.23 533 query - 533 1e-80 250.0 0.0 1 1 "
    "1e-82 1e-80 245.0 0.0 1 533 2 533 1 533 0.99 "
    "Carotenoid oxygenase/RPE65 family\n"
)
RPE65_UNIPROT_ENTRY = """\
ID   RPE65_HUMAN              Reviewed;         533 AA.
AC   Q16518;
GN   Name=RPE65;
FT   BINDING         180
FT                   /note="Iron-binding site"
FT   BINDING         241
FT                   /note="Iron-binding site"
FT   BINDING         313
FT                   /note="Iron-binding site"
FT   BINDING         527
FT                   /note="Iron-binding site"
FT   LIPID           112
FT                   /note="S-palmitoyl cysteine; in membrane form"
FT   LIPID           231
FT                   /note="S-palmitoyl cysteine; in membrane form"
FT   LIPID           329
FT                   /note="S-palmitoyl cysteine; in membrane form"
FT   LIPID           330
FT                   /note="S-palmitoyl cysteine; in membrane form"
//
"""
PCARE_UNIPROT_ENTRY = """\
ID   PCARE_HUMAN              Reviewed;        1289 AA.
AC   Q8N118;
GN   Name=PCARE; Synonyms=C2orf71;
FT   COILED          171..338
FT                   /note="Helical/coiled-coil region"
FT   MOTIF           597..615
FT                   /note="WH2"
FT   REGION          1013..1095
FT                   /note="Proline-rich domain"
FT   MOTIF           1042..1049
FT                   /note="Nuclear localization signal"
//
"""
USH2A_UNIPROT_ENTRY = """\
ID   USH2A_HUMAN              Reviewed;        5202 AA.
AC   O75445;
GN   Name=USH2A; Synonyms=USH2;
FT   DOMAIN          27..284
FT                   /note="Laminin N-terminal"
FT   DOMAIN          1002..1042
FT                   /note="Laminin EGF-like 1"
FT   DOMAIN          1714..1891
FT                   /note="Laminin G-like 2"
FT   DOMAIN          2015..2093
FT                   /note="Fibronectin type-III 1"
FT   REGION          1002..1042
FT                   /note="Collagen IV/fibronectin interaction region"
FT   SIGNAL          1..31
FT   TOPO_DOM        32..5042
FT                   /note="Extracellular"
FT   TRANSMEM        5043..5063
FT                   /note="Helical"
FT   TOPO_DOM        5064..5202
FT                   /note="Cytoplasmic"
FT   MOTIF           5200..5202
FT                   /note="PDZ-binding"
//
"""
DNM1_UNIPROT_ENTRY = """\
ID   DNM1_HUMAN               Reviewed;         864 AA.
AC   Q05193;
GN   Name=DNM1;
FT   DOMAIN          39..312
FT                   /note="Dynamin-type G domain"
FT   REGION          319..495
FT                   /note="Middle/stalk domain"
FT   DOMAIN          515..625
FT                   /note="Pleckstrin homology domain"
FT   DOMAIN          659..750
FT                   /note="GTPase effector domain"
FT   REGION          746..864
FT                   /note="Proline-rich domain"
//
"""
FZD5_UNIPROT_ENTRY = """\
ID   FZD5_HUMAN               Reviewed;         585 AA.
AC   Q13467;
GN   Name=FZD5;
FT   SIGNAL          1..26
FT   TOPO_DOM        27..238
FT                   /note="Extracellular"
FT   TRANSMEM        239..259
FT                   /note="Helical; Name=1"
FT   TOPO_DOM        260..270
FT                   /note="Cytoplasmic"
FT   TRANSMEM        271..291
FT                   /note="Helical; Name=2"
FT   TOPO_DOM        292..315
FT                   /note="Extracellular"
FT   TRANSMEM        316..336
FT                   /note="Helical; Name=3"
FT   TOPO_DOM        337..358
FT                   /note="Cytoplasmic"
FT   TRANSMEM        359..379
FT                   /note="Helical; Name=4"
FT   TOPO_DOM        380..402
FT                   /note="Extracellular"
FT   TRANSMEM        403..423
FT                   /note="Helical; Name=5"
FT   TOPO_DOM        424..449
FT                   /note="Cytoplasmic"
FT   TRANSMEM        450..470
FT                   /note="Helical; Name=6"
FT   TOPO_DOM        471..500
FT                   /note="Extracellular"
FT   TRANSMEM        501..521
FT                   /note="Helical; Name=7"
FT   TOPO_DOM        522..585
FT                   /note="Cytoplasmic"
FT   DOMAIN          28..150
FT                   /note="FZ"
FT   MOTIF           525..530
FT                   /note="Lys-Thr-X-X-X-Trp motif"
FT   MOTIF           583..585
FT                   /note="PDZ-binding"
//
"""

REFERENCE_CONTROL_CASES = (
    ("RPE65", "RPE65 NM_000329.3 reference control", "M" + "A" * 532),
    ("USH2A", "USH2A reference control", "M" + "S" * 899),
    ("PCARE", "PCARE NM_001029883 reference control", "M" + "P" * 719),
    ("DNM1", "DNM1 reference control", "M" + "D" * 863),
    ("FZD5", "FZD5 reference control", "M" + "F" * 584),
)


class ReadyHmmerRunner:
    def __init__(self, domtblout: str = DOMTBLOUT) -> None:
        self.domtblout = domtblout
        self.calls = 0

    def status(self) -> HmmerRuntimeStatus:
        return HmmerRuntimeStatus(
            ready=True,
            hmmscan_path="hmmscan",
            pfam_hmm_path="Pfam-A.hmm",
        )

    def run(self, *, protein_sequence: str, sequence_hash: str) -> str:
        self.calls += 1
        assert protein_sequence
        assert sequence_hash
        return self.domtblout


class UnavailableHmmerRunner:
    def __init__(self, reason: str = "hmmscan_executable_missing") -> None:
        self.reason = reason
        self.calls = 0

    def status(self) -> HmmerRuntimeStatus:
        return HmmerRuntimeStatus(
            ready=False,
            reason=self.reason,
            warnings=(self.reason,),
        )

    def run(self, *, protein_sequence: str, sequence_hash: str) -> str:
        self.calls += 1
        raise AssertionError("hmmscan should not run when runtime status is unavailable")


class MemoryProteinAnnotationCache:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str, str | None], ProteinDomainTrack] = {}

    def get(
        self,
        *,
        sequence_hash: str,
        pfam_release: str,
        hmmer_release: str,
        uniprot_release: str | None = None,
    ) -> ProteinDomainTrack | None:
        return self.records.get((sequence_hash, pfam_release, hmmer_release, uniprot_release))

    def upsert(self, track: ProteinDomainTrack) -> None:
        assert track.protein_sequence_hash
        assert track.pfam_release
        assert track.hmmer_release
        self.records[
            (
                track.protein_sequence_hash,
                track.pfam_release,
                track.hmmer_release,
                track.uniprot_release,
            )
        ] = track


@pytest.mark.parametrize(("gene", "label", "protein_sequence"), REFERENCE_CONTROL_CASES)
def test_reference_control_cases_run_local_hmmer_without_variant_markers(
    gene: str,
    label: str,
    protein_sequence: str,
) -> None:
    runner = ReadyHmmerRunner()
    service = ProteinAnnotationService(
        settings=Settings(jwt_secret="test-secret", protein_annotation_enabled=True),
        cache_repo=MemoryProteinAnnotationCache(),
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence=protein_sequence,
            input_type="protein",
            sequence_label=label,
            gene_symbol=gene,
            use_cache=True,
            allow_run=True,
        )
    )

    assert track.status == "available"
    assert track.sequence_label == label
    assert track.gene_symbol == gene
    assert track.translated_from == "protein"
    assert track.variant_markers == []
    assert track.features[0].label == "Reference control domain"
    assert track.features[0].aa_start == 12
    assert track.features[0].aa_end == 95
    assert track.provenance
    assert runner.calls == 1
    assert gene in label


def test_sequence_normalization_preserves_selenocysteine_for_protein_input() -> None:
    protein = normalize_protein_input("MUG*", input_type="protein")
    coding = normalize_protein_input("AUGGCTTAA", input_type="coding_dna")

    assert protein.protein_sequence == "MUG"
    assert coding.protein_sequence == "MA"
    assert coding.warnings == ("terminal_stop_codon_removed",)


def test_parse_hmmer_domtblout_maps_domain_coordinates_and_provenance() -> None:
    features = parse_hmmer_domtblout(
        DOMTBLOUT,
        pfam_release="Pfam 37.4",
        pfam_checksum_sha256="abc123",
    )

    assert len(features) == 1
    feature = features[0]
    assert feature.accession == "PF00001.1"
    assert feature.source == "Pfam/HMMER hmmscan"
    assert feature.source_release == "Pfam 37.4"
    assert feature.source_checksum_sha256 == "abc123"
    assert feature.score == 75.0
    assert feature.e_value == 1e-20
    assert feature.hmm_start == 2
    assert feature.hmm_end == 90
    assert feature.envelope_start == 10
    assert feature.envelope_end == 99


def test_uniprot_flatfile_parser_preserves_specific_pcare_feature_names() -> None:
    features = parse_uniprot_flatfile_features(
        PCARE_UNIPROT_ENTRY,
        protein_length=1289,
        source_release="UniProtKB 2026_02",
        source_checksum_sha256="feedface",
    )

    labels = {feature.label: feature for feature in features}
    assert set(labels) == {
        "Helical/coiled-coil region",
        "WH2",
        "Proline-rich domain",
        "Nuclear localization signal",
    }
    assert labels["Helical/coiled-coil region"].kind == "coiled_coil"
    assert labels["Helical/coiled-coil region"].aa_start == 171
    assert labels["WH2"].kind == "motif"
    assert labels["WH2"].aa_start == 597
    assert labels["Proline-rich domain"].kind == "region"
    assert labels["Nuclear localization signal"].kind == "motif"
    assert labels["Proline-rich domain"].short_label == "PRD"
    assert labels["Nuclear localization signal"].short_label == "NLS"
    assert all(feature.source == "UniProtKB/Swiss-Prot feature table" for feature in features)


def test_uniprot_flatfile_parser_preserves_specific_rpe65_sites() -> None:
    features = parse_uniprot_flatfile_features(
        RPE65_UNIPROT_ENTRY,
        protein_length=533,
        source_release="UniProtKB 2026_02",
        source_checksum_sha256="feedface",
    )

    labels = {}
    for feature in features:
        labels.setdefault(feature.label, []).append(feature)

    assert len(labels["Iron-binding site"]) == 4
    assert {feature.aa_start for feature in labels["Iron-binding site"]} == {
        180,
        241,
        313,
        527,
    }
    assert all(feature.kind == "site" for feature in labels["Iron-binding site"])
    assert all(feature.short_label == "Fe" for feature in labels["Iron-binding site"])
    assert len(labels["S-palmitoyl cysteine; in membrane form"]) == 4
    assert {feature.aa_start for feature in labels["S-palmitoyl cysteine; in membrane form"]} == {
        112,
        231,
        329,
        330,
    }
    assert all(
        feature.short_label == "Palm"
        for feature in labels["S-palmitoyl cysteine; in membrane form"]
    )
    assert "Signal peptide" not in labels


def test_uniprot_flatfile_parser_preserves_specific_ush2a_architecture_features() -> None:
    features = parse_uniprot_flatfile_features(
        USH2A_UNIPROT_ENTRY,
        protein_length=5202,
        source_release="UniProtKB 2026_02",
        source_checksum_sha256="feedface",
    )

    labels = {feature.label: feature for feature in features}
    assert "Laminin N-terminal" in labels
    assert "Laminin EGF-like 1" in labels
    assert "Laminin G-like 2" in labels
    assert "Fibronectin type-III 1" in labels
    assert "Collagen IV/fibronectin interaction region" in labels
    assert labels["Laminin G-like 2"].kind == "domain"
    assert labels["Laminin G-like 2"].short_label == "LamG"
    assert labels["Fibronectin type-III 1"].kind == "domain"
    assert labels["Fibronectin type-III 1"].short_label == "FN3"
    assert labels["Collagen IV/fibronectin interaction region"].kind == "region"
    assert labels["Signal peptide"].kind == "signal_peptide"
    assert labels["Signal peptide"].short_label == "SP"
    assert labels["Signal peptide"].aa_start == 1
    assert labels["Signal peptide"].aa_end == 31
    assert labels["Helical"].kind == "transmembrane"
    assert labels["Helical"].short_label == "TM"
    assert labels["Helical"].aa_start == 5043
    assert labels["Helical"].aa_end == 5063
    assert labels["PDZ-binding"].kind == "motif"
    assert labels["PDZ-binding"].short_label == "PDZ-binding"
    assert labels["PDZ-binding"].aa_start == 5200
    assert labels["PDZ-binding"].aa_end == 5202
    assert labels["Extracellular"].lane == "topology"
    assert labels["Cytoplasmic"].lane == "topology"


def test_uniprot_flatfile_parser_preserves_specific_dnm1_domain_names() -> None:
    features = parse_uniprot_flatfile_features(
        DNM1_UNIPROT_ENTRY,
        protein_length=864,
        source_release="UniProtKB 2026_02",
        source_checksum_sha256="feedface",
    )

    labels = {feature.label: feature for feature in features}
    assert labels["Dynamin-type G domain"].kind == "domain"
    assert labels["Dynamin-type G domain"].aa_start == 39
    assert labels["Dynamin-type G domain"].short_label == "GTPase"
    assert labels["Middle/stalk domain"].kind == "region"
    assert labels["Middle/stalk domain"].short_label == "Middle"
    assert labels["Pleckstrin homology domain"].kind == "domain"
    assert labels["Pleckstrin homology domain"].aa_start == 515
    assert labels["Pleckstrin homology domain"].short_label == "PH"
    assert labels["GTPase effector domain"].kind == "domain"
    assert labels["GTPase effector domain"].aa_start == 659
    assert labels["GTPase effector domain"].short_label == "GED"
    assert labels["Proline-rich domain"].kind == "region"
    assert labels["Proline-rich domain"].short_label == "PRD"


def test_uniprot_flatfile_parser_preserves_specific_fzd5_receptor_topology() -> None:
    features = parse_uniprot_flatfile_features(
        FZD5_UNIPROT_ENTRY,
        protein_length=585,
        source_release="UniProtKB 2026_02",
        source_checksum_sha256="feedface",
    )

    labels = {feature.label: feature for feature in features}
    transmembrane_features = [feature for feature in features if feature.kind == "transmembrane"]

    assert labels["Signal peptide"].kind == "signal_peptide"
    assert labels["Signal peptide"].short_label == "SP"
    assert labels["FZ"].kind == "domain"
    assert labels["FZ"].short_label == "CRD"
    assert labels["FZ"].description == "WNT-binding Frizzled cysteine-rich domain"
    assert labels["FZ"].aa_start == 28
    assert labels["Extracellular"].kind == "topological_domain"
    assert labels["Extracellular"].short_label == "Extra"
    assert labels["Cytoplasmic"].kind == "topological_domain"
    assert labels["Cytoplasmic"].short_label == "Cyto"
    assert len(transmembrane_features) == 7
    assert {feature.short_label for feature in transmembrane_features} == {
        "TM1",
        "TM2",
        "TM3",
        "TM4",
        "TM5",
        "TM6",
        "TM7",
    }
    assert "PDZ-binding" in labels
    assert all(feature.lane == "topology" for feature in transmembrane_features)


def test_uniprot_provider_retrieves_specific_features_by_gene_without_gene_hardcode(
    tmp_path: Path,
) -> None:
    flatfile_path = tmp_path / "uniprot_sprot.dat"
    flatfile_path.write_text(
        RPE65_UNIPROT_ENTRY + PCARE_UNIPROT_ENTRY,
        encoding="utf-8",
    )
    provider = UniProtFlatfileFeatureProvider(
        Settings(
            jwt_secret="test-secret",
            protein_annotation_uniprot_dat_path=flatfile_path,
            protein_annotation_uniprot_feature_index_path=tmp_path / "missing.features.jsonl",
        )
    )

    result = provider.features_for_request(
        ProteinAnnotationRequest(
            sequence="M" + "P" * 1288,
            input_type="protein",
            gene_symbol="PCARE",
            transcript="NM_001029883",
        ),
        protein_length=1289,
    )

    assert not result.warnings
    assert {feature.label for feature in result.features} >= {
        "WH2",
        "Proline-rich domain",
        "Nuclear localization signal",
    }
    assert all(feature.accession == "Q8N118" for feature in result.features)


def test_uniprot_feature_index_retrieves_reference_architecture_matrix(tmp_path: Path) -> None:
    flatfile_path = tmp_path / "uniprot_sprot.dat"
    flatfile_path.write_text(
        RPE65_UNIPROT_ENTRY
        + PCARE_UNIPROT_ENTRY
        + USH2A_UNIPROT_ENTRY
        + DNM1_UNIPROT_ENTRY
        + FZD5_UNIPROT_ENTRY,
        encoding="utf-8",
    )
    index_path = tmp_path / "uniprot_sprot.features.jsonl"

    summary = write_uniprot_feature_index(flatfile_path, index_path)

    assert summary["records"] == 5
    assert index_path.is_file()

    provider = UniProtFlatfileFeatureProvider(
        Settings(
            jwt_secret="test-secret",
            protein_annotation_uniprot_dat_path=tmp_path / "missing.dat.gz",
            protein_annotation_uniprot_feature_index_path=index_path,
            protein_annotation_uniprot_scan_timeout_seconds=1,
        )
    )
    cases = [
        (
            "RPE65",
            533,
            {
                "Iron-binding site": ("site", "Fe", 180, 180),
                "S-palmitoyl cysteine; in membrane form": ("site", "Palm", 112, 112),
            },
        ),
        (
            "PCARE",
            1289,
            {
                "Helical/coiled-coil region": ("coiled_coil", "CC", 171, 338),
                "WH2": ("motif", "WH2", 597, 615),
                "Proline-rich domain": ("region", "PRD", 1013, 1095),
                "Nuclear localization signal": ("motif", "NLS", 1042, 1049),
            },
        ),
        (
            "USH2A",
            5202,
            {
                "Signal peptide": ("signal_peptide", "SP", 1, 31),
                "Laminin G-like 2": ("domain", "LamG", 1714, 1891),
                "Helical": ("transmembrane", "TM", 5043, 5063),
                "PDZ-binding": ("motif", "PDZ-binding", 5200, 5202),
            },
        ),
        (
            "DNM1",
            864,
            {
                "Dynamin-type G domain": ("domain", "GTPase", 39, 312),
                "Middle/stalk domain": ("region", "Middle", 319, 495),
                "Pleckstrin homology domain": ("domain", "PH", 515, 625),
                "GTPase effector domain": ("domain", "GED", 659, 750),
                "Proline-rich domain": ("region", "PRD", 746, 864),
            },
        ),
        (
            "FZD5",
            585,
            {
                "Signal peptide": ("signal_peptide", "SP", 1, 26),
                "FZ": ("domain", "CRD", 28, 150),
                "PDZ-binding": ("motif", "PDZ-binding", 583, 585),
            },
        ),
    ]

    for gene, protein_length, expected in cases:
        result = provider.features_for_request(
            ProteinAnnotationRequest(
                sequence="M" + "A" * (protein_length - 1),
                input_type="protein",
                gene_symbol=gene,
            ),
            protein_length=protein_length,
        )
        labels: dict[str, list] = {}
        for feature in result.features:
            labels.setdefault(feature.label, []).append(feature)
        for label, (kind, short_label, start, end) in expected.items():
            assert any(
                feature.kind == kind
                and feature.short_label == short_label
                and feature.aa_start == start
                and feature.aa_end == end
                and feature.source == "UniProtKB/Swiss-Prot feature table"
                for feature in labels[label]
            )

    fzd5 = provider.features_for_request(
        ProteinAnnotationRequest(
            sequence="M" + "A" * 584,
            input_type="protein",
            gene_symbol="FZD5",
        ),
        protein_length=585,
    )
    assert len([feature for feature in fzd5.features if feature.kind == "transmembrane"]) == 7


def test_uniprot_feature_index_cli_builds_compact_index(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    flatfile_path = tmp_path / "uniprot_sprot.dat"
    output_path = tmp_path / "uniprot_sprot.features.jsonl"
    flatfile_path.write_text(USH2A_UNIPROT_ENTRY + FZD5_UNIPROT_ENTRY, encoding="utf-8")

    exit_code = uniprot_feature_index_main(
        [
            "--input",
            str(flatfile_path),
            "--output",
            str(output_path),
            "--compact",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["records"] == 2
    assert payload["features"] > 0
    assert output_path.read_text(encoding="utf-8").count("\n") == 2


def test_service_merges_rpe65_uniprot_sites_with_local_hmmer_hits(tmp_path: Path) -> None:
    flatfile_path = tmp_path / "uniprot_sprot.dat"
    flatfile_path.write_text(RPE65_UNIPROT_ENTRY, encoding="utf-8")
    settings = Settings(
        jwt_secret="test-secret",
        protein_annotation_enabled=True,
        protein_annotation_uniprot_features_enabled=True,
        protein_annotation_uniprot_dat_path=flatfile_path,
        protein_annotation_uniprot_feature_index_path=tmp_path / "missing.features.jsonl",
    )
    runner = ReadyHmmerRunner(domtblout=RPE65_DOMTBLOUT)
    service = ProteinAnnotationService(
        settings=settings,
        cache_repo=MemoryProteinAnnotationCache(),
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence="M" + "A" * 532,
            input_type="protein",
            sequence_label="RPE65 NM_000329.3 reference control",
            gene_symbol="RPE65",
            transcript="NM_000329.3",
            allow_run=True,
        )
    )

    labels = {}
    for feature in track.features:
        labels.setdefault(feature.label, []).append(feature)

    assert track.status == "available"
    assert len(labels["Iron-binding site"]) == 4
    assert len(labels["S-palmitoyl cysteine; in membrane form"]) == 4
    assert labels["Carotenoid oxygenase/RPE65 family"][0].source == "Pfam/HMMER hmmscan"
    assert labels["Carotenoid oxygenase/RPE65 family"][0].accession == "PF03055.23"
    assert labels["Carotenoid oxygenase/RPE65 family"][0].short_label == "RPE65 cat."
    assert (
        labels["Carotenoid oxygenase/RPE65 family"][0].description
        == "Carotenoid oxygenase/RPE65 catalytic family domain"
    )


def test_protein_features_from_domain_track_adds_rpe65_architecture_seed() -> None:
    features = protein_features_from_domain_track(
        ProteinFeatures(),
        ProteinDomainTrack(
            status="cache_hit",
            gene_symbol="RPE65",
            protein_length=533,
            features=[],
        ),
    )

    assert features.domain_track is not None
    assert features.domain_track.status == "cache_hit"
    assert "bundled_protein_feature_seed:RPE65" in features.domain_track.warnings
    assert {
        feature.aa_start
        for feature in features.domain_track.features
        if feature.label == "Amphipathic helix (membrane contact)"
    } == {110, 200}
    assert {site.aa for site in features.active_sites} == {180, 241, 313, 527}
    assert all(site.residue == "H" for site in features.active_sites)
    assert {site.aa for site in features.palmitoylation} == {112, 231, 329, 330}
    assert all(site.residue == "C" for site in features.palmitoylation)
    assert {(region.aa_start, region.aa_end) for region in features.membrane_binding} == {
        (110, 127),
        (200, 215),
    }


def test_service_recomputes_stale_pfam_only_cache_when_uniprot_features_enabled(
    tmp_path: Path,
) -> None:
    flatfile_path = tmp_path / "uniprot_sprot.dat"
    flatfile_path.write_text(USH2A_UNIPROT_ENTRY, encoding="utf-8")
    sequence = "M" + "A" * 5201
    normalized = normalize_protein_input(sequence, input_type="protein")
    pfam_release = DEFAULT_DATA_SOURCE_REGISTRY.get("interpro_pfam_protein_matches").source_version
    hmmer_release = DEFAULT_DATA_SOURCE_REGISTRY.get("hmmer_pfam_a").source_version
    uniprot_release = DEFAULT_DATA_SOURCE_REGISTRY.get(
        "uniprotkb_reviewed_swissprot"
    ).source_version
    cache = MemoryProteinAnnotationCache()
    cache.upsert(
        ProteinDomainTrack(
            status="available",
            protein_sequence_hash=normalized.sequence_hash,
            protein_length=len(normalized.protein_sequence),
            translated_from="protein",
            cache_key=(
                f"protein_annotation:sha256:{normalized.sequence_hash}:"
                f"pfam:{pfam_release}:hmmer:{hmmer_release}:uniprot:{uniprot_release}"
            ),
            cache_status="stored",
            pfam_release=pfam_release,
            hmmer_release=hmmer_release,
            uniprot_release=uniprot_release,
            features=parse_hmmer_domtblout(
                DOMTBLOUT,
                pfam_release=pfam_release,
                pfam_checksum_sha256="abc123",
            ),
        )
    )
    service = ProteinAnnotationService(
        settings=Settings(
            jwt_secret="test-secret",
            protein_annotation_enabled=True,
            protein_annotation_uniprot_features_enabled=True,
            protein_annotation_uniprot_dat_path=flatfile_path,
            protein_annotation_uniprot_feature_index_path=tmp_path / "missing.features.jsonl",
            protein_annotation_hmmscan_max_residues=6000,
        ),
        cache_repo=cache,
        runner=ReadyHmmerRunner(domtblout=DOMTBLOUT),
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence=sequence,
            input_type="protein",
            sequence_label="USH2A reference",
            gene_symbol="USH2A",
            allow_run=True,
        )
    )

    labels = {feature.label: feature for feature in track.features}
    assert track.status == "available"
    assert "protein_annotation_cache_hit" not in track.warnings
    assert "uniprot_feature_table_checked" in track.warnings
    assert "Signal peptide" in labels
    assert labels["Helical"].kind == "transmembrane"
    assert labels["PDZ-binding"].kind == "motif"


def test_feature_flag_off_uses_legacy_release_cache_for_large_protein_without_hmmer() -> None:
    sequence = "M" + "A" * 5201
    normalized = normalize_protein_input(sequence, input_type="protein")
    pfam_release = DEFAULT_DATA_SOURCE_REGISTRY.get("interpro_pfam_protein_matches").source_version
    hmmer_release = DEFAULT_DATA_SOURCE_REGISTRY.get("hmmer_pfam_a").source_version
    uniprot_release = DEFAULT_DATA_SOURCE_REGISTRY.get(
        "uniprotkb_reviewed_swissprot"
    ).source_version
    cache = MemoryProteinAnnotationCache()
    cache.upsert(
        ProteinDomainTrack(
            status="available",
            protein_sequence_hash=normalized.sequence_hash,
            protein_length=len(normalized.protein_sequence),
            translated_from="protein",
            cache_key=(
                f"protein_annotation:sha256:{normalized.sequence_hash}:"
                f"pfam:{pfam_release}:hmmer:{hmmer_release}:uniprot:{uniprot_release}"
            ),
            cache_status="stored",
            pfam_release=pfam_release,
            hmmer_release=hmmer_release,
            uniprot_release=uniprot_release,
            features=parse_hmmer_domtblout(
                DOMTBLOUT,
                pfam_release=pfam_release,
                pfam_checksum_sha256="abc123",
            ),
        )
    )
    runner = ReadyHmmerRunner()
    service = ProteinAnnotationService(
        settings=Settings(
            jwt_secret="test-secret",
            protein_annotation_enabled=True,
            protein_annotation_uniprot_features_enabled=False,
        ),
        cache_repo=cache,
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence=sequence,
            input_type="protein",
            sequence_label="USH2A reference",
            gene_symbol="USH2A",
            allow_run=True,
        )
    )

    assert track.status == "cache_hit"
    assert track.uniprot_release == uniprot_release
    assert "protein_annotation_cache_hit" in track.warnings
    assert runner.calls == 0


def test_cache_miss_skips_hmmer_for_large_protein_without_uniprot_features() -> None:
    runner = ReadyHmmerRunner()
    service = ProteinAnnotationService(
        settings=Settings(
            jwt_secret="test-secret",
            protein_annotation_enabled=True,
            protein_annotation_uniprot_features_enabled=False,
            protein_annotation_hmmscan_max_residues=5000,
        ),
        cache_repo=MemoryProteinAnnotationCache(),
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence="M" + "A" * 5201,
            input_type="protein",
            sequence_label="USH2A reference",
            gene_symbol="USH2A",
            allow_run=True,
        )
    )

    assert track.status == "unavailable"
    assert track.fail_closed_reason == "protein_annotation_hmmscan_sequence_too_long"
    assert "protein_annotation_hmmscan_max_residues:5000" in track.warnings
    assert runner.calls == 0


def test_zero_hmmscan_cap_uses_safe_default_not_unbounded() -> None:
    runner = ReadyHmmerRunner()
    service = ProteinAnnotationService(
        settings=Settings(
            jwt_secret="test-secret",
            protein_annotation_enabled=True,
            protein_annotation_hmmscan_max_residues=0,
        ),
        cache_repo=MemoryProteinAnnotationCache(),
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence="M" + "A" * 5201,
            input_type="protein",
            sequence_label="USH2A reference",
            gene_symbol="USH2A",
            allow_run=True,
        )
    )

    assert track.status == "unavailable"
    assert track.fail_closed_reason == "protein_annotation_hmmscan_sequence_too_long"
    assert "protein_annotation_hmmscan_max_residues:5000" in track.warnings
    assert runner.calls == 0


def test_service_returns_uniprot_feature_index_partial_track_when_hmmer_unavailable(
    tmp_path: Path,
) -> None:
    flatfile_path = tmp_path / "uniprot_sprot.dat"
    flatfile_path.write_text(USH2A_UNIPROT_ENTRY, encoding="utf-8")
    index_path = tmp_path / "uniprot_sprot.features.jsonl"
    write_uniprot_feature_index(flatfile_path, index_path)
    runner = UnavailableHmmerRunner()
    service = ProteinAnnotationService(
        settings=Settings(
            jwt_secret="test-secret",
            protein_annotation_enabled=True,
            protein_annotation_uniprot_features_enabled=True,
            protein_annotation_uniprot_dat_path=tmp_path / "missing.dat.gz",
            protein_annotation_uniprot_feature_index_path=index_path,
        ),
        cache_repo=MemoryProteinAnnotationCache(),
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence="M" + "A" * 5201,
            input_type="protein",
            sequence_label="USH2A reference",
            gene_symbol="USH2A",
            allow_run=True,
        )
    )

    labels = {feature.label: feature for feature in track.features}
    assert track.status == "partial"
    assert track.fail_closed_reason == "hmmscan_executable_missing"
    assert "uniprot_feature_table_checked" in track.warnings
    assert "no_live_protein_api_fallback" in track.warnings
    assert "Signal peptide" in labels
    assert labels["Helical"].kind == "transmembrane"
    assert labels["PDZ-binding"].kind == "motif"
    assert runner.calls == 0


def test_cache_hit_is_fail_closed_to_local_cache_without_runner_call() -> None:
    normalized = normalize_protein_input("MAAAA", input_type="protein")
    pfam_release = DEFAULT_DATA_SOURCE_REGISTRY.get("interpro_pfam_protein_matches").source_version
    hmmer_release = DEFAULT_DATA_SOURCE_REGISTRY.get("hmmer_pfam_a").source_version
    cache = MemoryProteinAnnotationCache()
    cache.upsert(
        ProteinDomainTrack(
            status="available",
            protein_sequence_hash=normalized.sequence_hash,
            protein_length=len(normalized.protein_sequence),
            translated_from="protein",
            cache_key="protein_annotation:test",
            cache_status="stored",
            pfam_release=pfam_release,
            hmmer_release=hmmer_release,
            uniprot_release=None,
            features=parse_hmmer_domtblout(
                DOMTBLOUT,
                pfam_release=pfam_release,
                pfam_checksum_sha256="abc123",
            ),
        )
    )
    runner = ReadyHmmerRunner()
    service = ProteinAnnotationService(
        settings=Settings(jwt_secret="test-secret", protein_annotation_enabled=True),
        cache_repo=cache,
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence="MAAAA",
            input_type="protein",
            sequence_label="RPE65 NM_000329.3 reference control",
            gene_symbol="RPE65",
            transcript="NM_000329.3",
            allow_run=True,
        )
    )

    assert track.status == "cache_hit"
    assert track.cache_status == "cache_hit"
    assert track.sequence_label == "RPE65 NM_000329.3 reference control"
    assert track.gene_symbol == "RPE65"
    assert "protein_annotation_cache_hit" in track.warnings
    assert runner.calls == 0


def test_disabled_runtime_fails_closed_without_live_api_fallback() -> None:
    runner = ReadyHmmerRunner()
    service = ProteinAnnotationService(
        settings=Settings(jwt_secret="test-secret", protein_annotation_enabled=False),
        cache_repo=MemoryProteinAnnotationCache(),
        runner=runner,
    )

    track = service.annotate(
        ProteinAnnotationRequest(
            sequence="MAAAA",
            input_type="protein",
            sequence_label="PCARE NM_001029883 reference control",
            gene_symbol="PCARE",
            transcript="NM_001029883",
        )
    )

    assert track.status == "unavailable"
    assert track.fail_closed_reason == "protein_annotation_disabled"
    assert "no_live_protein_api_fallback" in track.warnings
    assert runner.calls == 0


def test_protein_annotation_endpoint_returns_disabled_fail_closed_state(client) -> None:
    response = client.post(
        "/api/v1/protein/annotate",
        json={
            "sequence": "MAAAA",
            "input_type": "protein",
            "sequence_label": "RPE65 NM_000329.3 reference control",
            "gene_symbol": "RPE65",
            "transcript": "NM_000329.3",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["fail_closed_reason"] == "protein_annotation_disabled"
    assert body["sequence_label"] == "RPE65 NM_000329.3 reference control"
    assert body["gene_symbol"] == "RPE65"
    assert "no_live_protein_api_fallback" in body["warnings"]


def test_protein_annotation_endpoint_forces_cache_only_even_if_client_allows_run(client) -> None:
    class CapturingProteinAnnotationService:
        def __init__(self) -> None:
            self.requests: list[ProteinAnnotationRequest] = []

        def annotate(self, request: ProteinAnnotationRequest) -> ProteinDomainTrack:
            self.requests.append(request)
            return ProteinDomainTrack(
                status="unavailable",
                fail_closed_reason="protein_annotation_cache_miss",
                cache_status="cache_miss",
                warnings=["protein_annotation_cache_miss_no_runtime_run"],
            )

    service = CapturingProteinAnnotationService()
    client.app.state.protein_annotation_service = service

    response = client.post(
        "/api/v1/protein/annotate",
        json={
            "sequence": "MAAAA",
            "input_type": "protein",
            "gene_symbol": "RPE65",
            "use_cache": False,
            "allow_run": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["fail_closed_reason"] == "protein_annotation_cache_miss"
    assert len(service.requests) == 1
    assert service.requests[0].allow_run is False
    assert service.requests[0].use_cache is True


def test_protein_asset_inspection_verifies_size_and_hashes(tmp_path: Path) -> None:
    content = b"protein-control"
    asset_path = tmp_path / "protein-control.bin"
    asset_path.write_bytes(content)
    asset = ProteinAssetSpec(
        asset_id="protein_control",
        source_ids=(),
        relative_path=str(asset_path),
        expected_size_bytes=len(content),
        expected_md5=md5(content).hexdigest(),
        expected_sha256=sha256(content).hexdigest(),
        role="unit_test_control_asset",
    )

    unverified = inspect_protein_annotation_asset(asset, verify_checksums=False)
    verified = inspect_protein_annotation_asset(asset, verify_checksums=True)

    assert unverified.status is ProteinAssetStatus.PRESENT_UNVERIFIED
    assert unverified.checksum_verified is False
    assert verified.status is ProteinAssetStatus.READY
    assert verified.checksum_verified is True


def test_protein_asset_inspection_fails_closed_on_size_mismatch(tmp_path: Path) -> None:
    asset_path = tmp_path / "protein-control.bin"
    asset_path.write_bytes(b"short")
    asset = ProteinAssetSpec(
        asset_id="protein_control",
        source_ids=(),
        relative_path=str(asset_path),
        expected_size_bytes=100,
        expected_md5="0" * 32,
        expected_sha256="0" * 64,
        role="unit_test_control_asset",
    )

    inspection = inspect_protein_annotation_asset(asset, verify_checksums=True)

    assert inspection.status is ProteinAssetStatus.SIZE_MISMATCH
    assert inspection.ready is False
    assert inspection.checksum_verified is False
