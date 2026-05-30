from __future__ import annotations

from types import SimpleNamespace

from app.core.config import Settings
from app.services.reference_genome import ReferenceWindow
from app.services.sequence_context import (
    EnsemblVariantSequenceResolver,
    MaterializedHg38SequenceResolver,
    WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE,
    NormalizedVariantQuery,
    SequenceContext,
    SequenceContextService,
    normalize_sequence_query,
    unsupported_input_warning,
)


def _settings(**overrides) -> Settings:
    return Settings(jwt_secret="test-secret", **overrides)


def test_normalize_sequence_query_reuses_canonical_transcript_for_cdna() -> None:
    query = normalize_sequence_query(" rpe65 ", " RPE65:c.260 A>G ")

    assert query.gene == "RPE65"
    assert query.hgvs == "c.260A>G"
    assert query.transcript_hgvs == "c.260A>G"
    assert query.resolver_transcript == "NM_000329.3"
    assert query.resolver_transcript_hgvs == "NM_000329.3:c.260A>G"
    assert query.kind == "cdna"


def test_fixture_mode_returns_rpe65_sequence_context() -> None:
    service = SequenceContextService(settings=_settings(use_real_apis=False))

    result = service.resolve(gene="RPE65", cdna="c.260A>G")

    assert result.warnings == []
    assert result.context is not None
    assert result.context.gene == "RPE65"
    assert result.context.cdna == "c.260A>G"
    assert result.context.transcript == "NM_000329.3"
    assert result.context.transcript_hgvs == "NM_000329.3:c.260A>G"
    assert result.context.genomic_hg38 == "1-68444869-T-C"
    assert result.context.window_sequence[result.context.target_offset] == "A"
    assert result.context.reference_base == "A"
    assert result.context.alternate_base == "G"
    assert result.context.source == "fixture"


def test_unsupported_input_returns_structured_warning_without_context() -> None:
    service = SequenceContextService(settings=_settings(use_real_apis=False))

    result = service.resolve(gene="RPE65", cdna="rs1645931040")

    assert result.context is None
    assert result.warnings == [unsupported_input_warning("rsid")]


def test_unsupported_species_returns_structured_warning_without_context() -> None:
    service = SequenceContextService(settings=_settings(use_real_apis=False))

    result = service.resolve(gene="RPE65", cdna="c.260A>G", species="mouse")

    assert result.context is None
    assert result.warnings == [unsupported_input_warning("species")]


def test_missing_fixture_context_returns_unavailable_warning() -> None:
    service = SequenceContextService(settings=_settings(use_real_apis=False))

    result = service.resolve(gene="RPE65", cdna="c.999A>G")

    assert result.context is None
    assert result.warnings == [WORKBENCH_SEQUENCE_CONTEXT_UNAVAILABLE]


def test_real_mode_resolver_hook_receives_normalized_query() -> None:
    class Resolver:
        def __init__(self) -> None:
            self.query: NormalizedVariantQuery | None = None

        def resolve(self, query: NormalizedVariantQuery, species: str) -> SequenceContext:
            self.query = query
            return SequenceContext(
                gene=query.gene,
                cdna=query.hgvs,
                transcript=query.resolver_transcript,
                transcript_hgvs=query.resolver_transcript_hgvs,
                query_kind=query.kind,
                species=species,
                genome_build="GRCh38",
                genomic_hg38="1-68444869-T-C",
                strand="-",
                window_sequence="ATGC",
                target_offset=1,
                reference_base="A",
                alternate_base="G",
                source="resolver",
            )

    resolver = Resolver()
    service = SequenceContextService(settings=_settings(use_real_apis=True), resolver=resolver)

    result = service.resolve(gene="rpe65", cdna="RPE65:c.260A>G")

    assert result.context is not None
    assert result.context.source == "resolver"
    assert resolver.query is not None
    assert resolver.query.gene == "RPE65"
    assert resolver.query.hgvs == "c.260A>G"
    assert resolver.query.resolver_transcript_hgvs == "NM_000329.3:c.260A>G"


def test_ensembl_resolver_builds_context_from_variant_validator_and_sequence(
    monkeypatch,
) -> None:
    class Response:
        def __init__(self, *, payload=None, text: str = "") -> None:
            self.payload = payload
            self.text = text

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    calls: list[str] = []

    def fake_get(url: str, **_kwargs):
        calls.append(url)
        if "VariantValidator" in url:
            return Response(
                payload={
                    "metadata": {},
                    "variant": {
                        "primary_assembly_loci": {
                            "grch38": {
                                "vcf": {
                                    "chr": "chr1",
                                    "pos": "10",
                                    "ref": "T",
                                    "alt": "C",
                                }
                            }
                        }
                    },
                }
            )
        return Response(text="AACGT")

    monkeypatch.setattr("app.services.sequence_context.httpx.get", fake_get)
    resolver = EnsemblVariantSequenceResolver(
        _settings(use_real_apis=True),
        flank_bp=2,
    )
    query = normalize_sequence_query("RPE65", "c.260A>G")

    context = resolver.resolve(query, "human")

    assert context is not None
    assert context.genomic_hg38 == "1-10-T-C"
    assert context.window_sequence == "AACGT"
    assert context.target_offset == 2
    assert context.reference_base == "T"
    assert context.alternate_base == "C"
    assert context.source == "resolver"
    assert "VariantValidator" in calls[0]
    assert "sequence/region/human/1:8..12:1" in calls[1]


def test_materialized_hg38_resolver_reads_private_runtime_asset(monkeypatch) -> None:
    class ReferenceStore:
        def __init__(self) -> None:
            self.closed = False

        def get_sequence(self, chrom: str, start: int, end: int, build: str | None = None):
            assert (chrom, start, end, build) == ("1", 8, 12, "GRCh38")
            return ReferenceWindow(
                requested_chrom=chrom,
                chrom="1",
                start=start,
                end=end,
                zero_based_start=7,
                zero_based_end_exclusive=12,
                sequence="AACGT",
                genome_build="GRCh38",
                source_id="ucsc_hg38_2bit",
            )

        def close(self) -> None:
            self.closed = True

    resolved = SimpleNamespace(
        source_id="ucsc_hg38_2bit",
        asset_role="reference_genome_2bit",
        byte_size=835393456,
        checksum_algorithm="md5",
        checksum_value="dcc3ea27079aa6dc3f9deccd7275e0f8",
    )
    store = ReferenceStore()

    monkeypatch.setattr(
        "app.services.sequence_context.resolve_hg38_materialized_runtime_asset",
        lambda *_args, **_kwargs: resolved,
    )
    monkeypatch.setattr(
        EnsemblVariantSequenceResolver,
        "_variant_validator_summary",
        lambda self, query: {"vcf": {"chr": "chr1", "pos": "10", "ref": "T", "alt": "C"}},
    )
    resolver = MaterializedHg38SequenceResolver(
        _settings(use_real_apis=True),
        materialization_store=object(),
        flank_bp=2,
        reference_store_factory=lambda _resolved: store,
    )
    query = normalize_sequence_query("RPE65", "c.260A>G")

    context = resolver.resolve(query, "human")

    assert context is not None
    assert context.genomic_hg38 == "1-10-T-C"
    assert context.window_sequence == "AACGT"
    assert context.source_metadata["sequence_source"] == "ucsc_hg38_2bit_materialized"
    assert context.source_metadata["checksum_value"] == resolved.checksum_value
    assert "object_path" not in context.source_metadata
    assert "path" not in context.source_metadata
    assert store.closed is True
