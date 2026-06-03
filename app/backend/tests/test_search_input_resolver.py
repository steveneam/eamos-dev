from __future__ import annotations

from app.core.config import Settings
from app.services.search_input_interpreter import SearchInputInterpreter
from app.services.search_input_resolver import EamosSearchInputResolver, parse_search_text


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


class _NoLocalCoordinateResolver:
    def resolve(self, **_kwargs):
        return None


def test_eamos_search_input_resolver_accepts_gnomad_variant_id() -> None:
    resolution = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve(
        gene="USH2A",
        cdna="chr1-216247118-C-A",
    )

    assert resolution.kind == "genomic"
    assert resolution.genomic_hg38 == "1-216247118-C-A"
    assert resolution.genomic_hgvs == "NC_000001.11:g.216247118C>A"
    assert resolution.source_inputs.gnomad == "1-216247118-C-A"
    assert resolution.source_inputs.spliceai == "1-216247118-C-A"
    assert resolution.source_inputs.variant_validator == "NC_000001.11:g.216247118C>A"
    assert resolution.source_inputs.ensembl_vep == "NC_000001.11:g.216247118C>A"
    assert resolution.source_inputs.clinvar == "NC_000001.11:g.216247118C>A"
    assert resolution.coordinate_resolution_audit.resolver_path == "submitted_genomic"
    assert resolution.coordinate_resolution_audit.used_submitted_genomic is True
    assert resolution.coordinate_resolution_audit.used_clinvar_for_coordinates is False


def test_eamos_search_input_resolver_accepts_refseq_genomic_hgvs() -> None:
    resolution = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve(
        gene="USH2A",
        cdna="NC_000001.11:g.216247118C>A",
    )

    assert resolution.kind == "genomic"
    assert resolution.genomic_hg38 == "1-216247118-C-A"
    assert resolution.genomic_hgvs == "NC_000001.11:g.216247118C>A"
    assert resolution.source_inputs.gnomad == "1-216247118-C-A"
    assert resolution.source_inputs.variant_validator == "NC_000001.11:g.216247118C>A"


def test_parse_search_text_accepts_gene_prefixed_cdna() -> None:
    parsed = parse_search_text("abca4:c.1622T>C")

    assert parsed.gene == "abca4"
    assert parsed.cdna == "c.1622T>C"
    assert parsed.transcript is None
    assert parsed.protein_change is None
    assert parsed.warnings == ()


def test_parse_search_text_accepts_transcript_gene_and_protein_alias() -> None:
    parsed = parse_search_text("NM_001089.3(ABCA3):c.875A>T (p.Glu292Val)")

    assert parsed.gene == "ABCA3"
    assert parsed.cdna == "c.875A>T"
    assert parsed.transcript == "NM_001089.3"
    assert parsed.protein_change == "p.Glu292Val"


def test_eamos_search_input_resolver_uses_fixture_rsid_candidates() -> None:
    resolution = EamosSearchInputResolver(_settings(use_real_apis=False)).resolve_text(
        "rs61752871",
    )

    assert resolution.kind == "rsid"
    assert resolution.rsid_candidates[0].gene == "RPE65"
    assert resolution.rsid_candidates[0].cdna == "c.271C>T"
    assert resolution.rsid_candidates[0].transcript == "NM_000329.3"
    assert resolution.rsid_candidates[0].genomic_hg38 == "1-68444858-G-A"
    assert resolution.coordinate_resolution_audit.resolver_path == "rsid_candidates"
    assert resolution.coordinate_resolution_audit.used_rsid_candidates is True


def test_search_input_interpreter_auto_resolves_fixture_rsid() -> None:
    interpretation = SearchInputInterpreter(settings=_settings(use_real_apis=False)).interpret(
        "rs61752871"
    )

    assert interpretation.mode == "auto_resolved"
    assert interpretation.gene == "RPE65"
    assert interpretation.cdna == "c.271C>T"
    assert interpretation.transcript == "NM_000329.3"
    assert interpretation.protein_change == "p.Arg91Trp"
    assert interpretation.genomic_hg38 == "1-68444858-G-A"


def test_search_input_interpreter_live_rsid_prefers_source_supported_allele(
    monkeypatch,
) -> None:
    def fake_get(url: str, **kwargs):
        assert "/vep/human/id/rs1801133" in url
        assert kwargs["params"]["hgvs"] == "1"
        return _Response(
            [
                {
                    "id": "rs1801133",
                    "seq_region_name": "1",
                    "start": 11796321,
                    "allele_string": "G/A/C",
                    "colocated_variants": [
                        {
                            "id": "rs1801133",
                            "frequencies": {"A": {"af": 0.2454}},
                            "clin_sig_allele": "A:benign",
                        }
                    ],
                    "transcript_consequences": [
                        {
                            "gene_symbol": "MTHFR",
                            "hgvsc": "ENST00000376590.9:c.665C>T",
                            "hgvsp": "ENSP00000365775.3:p.Ala222Val",
                            "mane_select": "NM_005957.5",
                            "canonical": 1,
                            "variant_allele": "A",
                            "biotype": "protein_coding",
                        },
                        {
                            "gene_symbol": "MTHFR",
                            "hgvsc": "ENST00000376590.9:c.665C>G",
                            "hgvsp": "ENSP00000365775.3:p.Ala222Gly",
                            "mane_select": "NM_005957.5",
                            "canonical": 1,
                            "variant_allele": "C",
                            "biotype": "protein_coding",
                        },
                    ],
                }
            ]
        )

    monkeypatch.setattr("app.services.search_input_resolver.httpx.get", fake_get)

    interpretation = SearchInputInterpreter(settings=_settings(use_real_apis=True)).interpret(
        "rs1801133"
    )

    assert interpretation.mode == "auto_resolved"
    assert interpretation.gene == "MTHFR"
    assert interpretation.cdna == "c.665C>T"
    assert interpretation.transcript == "NM_005957.5"
    assert interpretation.protein_change == "p.Ala222Val"
    assert interpretation.genomic_hg38 == "1-11796321-G-A"
    assert "multiallelic" in interpretation.assumptions[1]
    assert "ensembl_vep_rsid_lookup" in interpretation.provenance


def test_eamos_search_input_resolver_accepts_spaced_genomic_search_text() -> None:
    resolution = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve_text(
        "6 31740453 G T",
    )

    assert resolution.kind == "genomic"
    assert resolution.hgvs == "6-31740453-G-T"
    assert resolution.genomic_hg38 == "6-31740453-G-T"
    assert resolution.genomic_hgvs == "NC_000006.12:g.31740453G>T"
    assert resolution.source_inputs.gnomad == "6-31740453-G-T"
    assert resolution.source_inputs.clinvar == "NC_000006.12:g.31740453G>T"


def test_eamos_search_input_resolver_accepts_colon_substitution_search_text() -> None:
    resolution = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve_text(
        "8:140300616 T>G",
    )

    assert resolution.kind == "genomic"
    assert resolution.hgvs == "8-140300616-T-G"
    assert resolution.genomic_hg38 == "8-140300616-T-G"
    assert resolution.genomic_hgvs == "NC_000008.11:g.140300616T>G"


def test_eamos_search_input_resolver_accepts_gnomad_style_indels() -> None:
    insertion = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve_text(
        "1-1042601-A-AGAGAG",
    )
    deletion = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve_text(
        "1-1042466-GGGC-G",
    )

    assert insertion.kind == "genomic"
    assert insertion.genomic_hg38 == "1-1042601-A-AGAGAG"
    assert insertion.genomic_hgvs == "NC_000001.11:g.1042601_1042602insGAGAG"
    assert insertion.source_inputs.variant_validator == insertion.genomic_hgvs
    assert insertion.source_inputs.clinvar == insertion.genomic_hgvs
    assert deletion.kind == "genomic"
    assert deletion.genomic_hg38 == "1-1042466-GGGC-G"
    assert deletion.genomic_hgvs == "NC_000001.11:g.1042467_1042469delGGC"
    assert deletion.source_inputs.variant_validator == deletion.genomic_hgvs
    assert deletion.source_inputs.clinvar == deletion.genomic_hgvs


def test_eamos_search_input_resolver_uses_grch38_nc_accession_versions() -> None:
    resolution = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve(
        gene="RPGRIP1",
        cdna="14-21324852-C-T",
    )

    assert resolution.kind == "genomic"
    assert resolution.genomic_hg38 == "14-21324852-C-T"
    assert resolution.genomic_hgvs == "NC_000014.9:g.21324852C>T"
    assert resolution.source_inputs.variant_validator == "NC_000014.9:g.21324852C>T"
    assert resolution.source_inputs.gnomad == "14-21324852-C-T"


def test_eamos_search_input_resolver_uses_mane_refseq_for_cdna_without_transcript(
    monkeypatch,
) -> None:
    def fake_get(url: str, **_kwargs):
        assert "lookup/symbol/homo_sapiens/USH2A" in url
        return _Response(
            {
                "Transcript": [
                    {
                        "id": "ENST00000307340",
                        "version": 8,
                        "biotype": "protein_coding",
                        "is_canonical": 1,
                        "MANE": [
                            {
                                "type": "MANE_Select",
                                "refseq_match": "NM_206933.4",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr("app.services.search_input_resolver.httpx.get", fake_get)

    resolution = EamosSearchInputResolver(_settings(use_real_apis=True)).resolve(
        gene="ush2a",
        cdna="c.2276G>T",
        protein_change="p.Cys759Phe",
    )

    assert resolution.gene == "USH2A"
    assert resolution.kind == "cdna"
    assert resolution.resolver_transcript == "NM_206933.4"
    assert resolution.resolver_transcript_hgvs == "NM_206933.4:c.2276G>T"
    assert resolution.source_inputs.variant_validator == "NM_206933.4:c.2276G>T"
    assert resolution.source_inputs.ensembl_vep == "NM_206933.4:c.2276G>T"
    assert resolution.source_inputs.clinvar == "NM_206933.4:c.2276G>T"
    assert "NM_206933.4:c.2276G>T" in resolution.source_inputs.literature_terms


def test_eamos_search_input_resolver_keeps_rpe65_splice_source_inputs() -> None:
    resolution = EamosSearchInputResolver(_settings(use_real_apis=False)).resolve(
        gene="RPE65",
        cdna="c.11+5G>A",
    )

    assert resolution.gene == "RPE65"
    assert resolution.kind == "cdna"
    assert resolution.resolver_transcript == "NM_000329.3"
    assert resolution.resolver_transcript_hgvs == "NM_000329.3:c.11+5G>A"
    assert resolution.source_inputs.variant_validator == "NM_000329.3:c.11+5G>A"
    assert resolution.source_inputs.ensembl_vep == "NM_000329.3:c.11+5G>A"
    assert resolution.source_inputs.clinvar == "NM_000329.3:c.11+5G>A"


def test_eamos_search_input_resolver_can_resolve_coordinates_when_enabled(
    monkeypatch,
) -> None:
    def fake_get(url: str, **_kwargs):
        if "lookup/symbol/homo_sapiens/USH2A" in url:
            return _Response(
                {
                    "Transcript": [
                        {
                            "id": "ENST00000307340",
                            "version": 8,
                            "biotype": "protein_coding",
                            "is_canonical": 1,
                            "MANE": [
                                {
                                    "type": "MANE_Select",
                                    "refseq_match": "NM_206933.4",
                                }
                            ],
                        }
                    ]
                }
            )
        assert "VariantValidator" in url
        return _Response(
            {
                "metadata": {},
                "variant": {
                    "gene_symbol": "USH2A",
                    "hgvs_transcript_variant": "NM_206933.4:c.2276G>T",
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000001.11:g.216247118C>A",
                            "vcf": {
                                "chr": "1",
                                "pos": "216247118",
                                "ref": "C",
                                "alt": "A",
                            },
                        }
                    },
                },
            }
        )

    monkeypatch.setattr("app.services.search_input_resolver.httpx.get", fake_get)

    resolution = EamosSearchInputResolver(
        _settings(use_real_apis=True),
        resolve_coordinates=True,
        local_coordinate_resolver=_NoLocalCoordinateResolver(),
    ).resolve(gene="USH2A", cdna="c.2276G>T")

    assert resolution.resolver_transcript_hgvs == "NM_206933.4:c.2276G>T"
    assert resolution.genomic_hg38 == "1-216247118-C-A"
    assert resolution.genomic_hgvs == "NC_000001.11:g.216247118C>A"
    assert resolution.source_inputs.gnomad == "1-216247118-C-A"
    assert resolution.variant_validator_summary is not None
    assert resolution.variant_validator_summary["variant_id"] == "1-216247118-C-A"
    assert resolution.coordinate_resolution_audit.resolver_path == "variant_validator_fallback"
    assert resolution.coordinate_resolution_audit.used_eamos_local is False
    assert resolution.coordinate_resolution_audit.used_variant_validator is True
    assert resolution.coordinate_resolution_audit.used_clinvar_for_coordinates is False


def test_eamos_search_input_resolver_covers_rpgrip1_cdna_stack(
    monkeypatch,
) -> None:
    def fake_get(url: str, **_kwargs):
        if "lookup/symbol/homo_sapiens/RPGRIP1" in url:
            return _Response(
                {
                    "Transcript": [
                        {
                            "id": "ENST00000400017",
                            "version": 7,
                            "biotype": "protein_coding",
                            "is_canonical": 1,
                            "MANE": [
                                {
                                    "type": "MANE_Select",
                                    "refseq_match": "NM_020366.4",
                                }
                            ],
                        }
                    ]
                }
            )
        assert "VariantValidator" in url
        return _Response(
            {
                "metadata": {},
                "variant": {
                    "gene_symbol": "RPGRIP1",
                    "hgvs_transcript_variant": "NM_020366.4:c.1997C>T",
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000014.9:g.21324852C>T",
                            "vcf": {
                                "chr": "14",
                                "pos": "21324852",
                                "ref": "C",
                                "alt": "T",
                            },
                        }
                    },
                },
            }
        )

    monkeypatch.setattr("app.services.search_input_resolver.httpx.get", fake_get)

    resolution = EamosSearchInputResolver(
        _settings(use_real_apis=True),
        resolve_coordinates=True,
        local_coordinate_resolver=_NoLocalCoordinateResolver(),
    ).resolve(gene="RPGRIP1", cdna="c.1997C>T")

    assert resolution.resolver_transcript == "NM_020366.4"
    assert resolution.resolver_transcript_hgvs == "NM_020366.4:c.1997C>T"
    assert resolution.genomic_hg38 == "14-21324852-C-T"
    assert resolution.genomic_hgvs == "NC_000014.9:g.21324852C>T"
    assert resolution.source_inputs.clinvar == "NC_000014.9:g.21324852C>T"
    assert resolution.source_inputs.gnomad == "14-21324852-C-T"


def test_eamos_search_input_resolver_covers_brca1_duplication_stack(
    monkeypatch,
) -> None:
    def fake_get(url: str, **_kwargs):
        if "lookup/symbol/homo_sapiens/BRCA1" in url:
            return _Response(
                {
                    "Transcript": [
                        {
                            "id": "ENST00000357654",
                            "version": 9,
                            "biotype": "protein_coding",
                            "is_canonical": 1,
                            "MANE": [
                                {
                                    "type": "MANE_Select",
                                    "refseq_match": "NM_007294.4",
                                }
                            ],
                        }
                    ]
                }
            )
        assert "VariantValidator" in url
        return _Response(
            {
                "metadata": {},
                "NM_007294.4:c.5266dup": {
                    "gene_symbol": "BRCA1",
                    "submitted_variant": "NM_007294.4:c.5266dupC",
                    "hgvs_transcript_variant": "NM_007294.4:c.5266dup",
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000017.11:g.43057065dup",
                            "vcf": {
                                "chr": "17",
                                "pos": "43057062",
                                "ref": "T",
                                "alt": "TG",
                            },
                        }
                    },
                    "selected_assembly": "GRCh38",
                },
            }
        )

    monkeypatch.setattr("app.services.search_input_resolver.httpx.get", fake_get)

    resolution = EamosSearchInputResolver(
        _settings(use_real_apis=True),
        resolve_coordinates=True,
        local_coordinate_resolver=_NoLocalCoordinateResolver(),
    ).resolve(gene="brca1", cdna="c.5266dupC")

    assert resolution.gene == "BRCA1"
    assert resolution.resolver_transcript == "NM_007294.4"
    assert resolution.resolver_transcript_hgvs == "NM_007294.4:c.5266dupC"
    assert resolution.variant_validator_summary is not None
    assert (
        resolution.variant_validator_summary["hgvs_transcript_variant"] == "NM_007294.4:c.5266dup"
    )
    assert resolution.genomic_hg38 == "17-43057062-T-TG"
    assert resolution.genomic_hgvs == "NC_000017.11:g.43057065dup"
    assert resolution.source_inputs.variant_validator == "NM_007294.4:c.5266dupC"
    assert resolution.source_inputs.gnomad == "17-43057062-T-TG"
    assert resolution.source_inputs.clinvar == "NC_000017.11:g.43057065dup"


def test_eamos_search_input_resolver_covers_brca1_duplication_stack_without_inserted_base(
    monkeypatch,
) -> None:
    def fake_get(url: str, **_kwargs):
        if "lookup/symbol/homo_sapiens/BRCA1" in url:
            return _Response(
                {
                    "Transcript": [
                        {
                            "id": "ENST00000357654",
                            "version": 9,
                            "biotype": "protein_coding",
                            "is_canonical": 1,
                            "MANE": [
                                {
                                    "type": "MANE_Select",
                                    "refseq_match": "NM_007294.4",
                                }
                            ],
                        }
                    ]
                }
            )
        assert "VariantValidator" in url
        return _Response(
            {
                "metadata": {},
                "NM_007294.4:c.5266dup": {
                    "gene_symbol": "BRCA1",
                    "submitted_variant": "NM_007294.4:c.5266dup",
                    "hgvs_transcript_variant": "NM_007294.4:c.5266dup",
                    "primary_assembly_loci": {
                        "grch38": {
                            "hgvs_genomic_description": "NC_000017.11:g.43057065dup",
                            "vcf": {
                                "chr": "17",
                                "pos": "43057062",
                                "ref": "T",
                                "alt": "TG",
                            },
                        }
                    },
                    "selected_assembly": "GRCh38",
                },
            }
        )

    monkeypatch.setattr("app.services.search_input_resolver.httpx.get", fake_get)

    resolution = EamosSearchInputResolver(
        _settings(use_real_apis=True),
        resolve_coordinates=True,
        local_coordinate_resolver=_NoLocalCoordinateResolver(),
    ).resolve(gene="brca1", cdna="c.5266dup")

    assert resolution.gene == "BRCA1"
    assert resolution.resolver_transcript == "NM_007294.4"
    assert resolution.genomic_hg38 == "17-43057062-T-TG"
    assert resolution.genomic_hgvs == "NC_000017.11:g.43057065dup"
    assert resolution.source_inputs.gnomad == "17-43057062-T-TG"
    assert resolution.source_inputs.clinvar == "NC_000017.11:g.43057065dup"
