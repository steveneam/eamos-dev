from __future__ import annotations


def test_panels_catalog_returns_launch_panels(client) -> None:
    response = client.get("/api/v1/panels")

    assert response.status_code == 200
    panels = response.json()["panels"]
    slugs = {panel["slug"] for panel in panels}
    assert {
        "inherited-retinal-disease",
        "cardiomyopathy-arrhythmia",
        "hereditary-cancer",
        "project-100-hardening",
    }.issubset(slugs)
    project_100 = next(panel for panel in panels if panel["slug"] == "project-100-hardening")
    assert project_100["gene_count"] == 10
    assert project_100["intervals_ref"] == "hg38"
    assert project_100["source"] == "custom"
    assert project_100["source_snapshot_v2"]["launch_posture"] == "unavailable"
    assert project_100["source_snapshot_v2"]["execution_disclosure"]["execution"] == ("unavailable")


def test_get_panel_returns_full_gene_list(client) -> None:
    response = client.get("/api/v1/panels/hereditary-cancer")

    assert response.status_code == 200
    panel = response.json()
    assert panel["slug"] == "hereditary-cancer"
    assert {gene["symbol"] for gene in panel["genes"]} >= {"BRCA1", "BRCA2", "TP53"}
    assert panel["source"] == "custom"
    assert panel["warnings"]
    snapshot = panel["source_snapshot_v2"]
    assert snapshot["artifact_manifest_id"] is None
    assert snapshot["artifact_sha256"] is None
    assert "PanelApp GEL remains disabled" in snapshot["execution_disclosure"]["warnings"][1]
    assert all(gene.get("interval_provenance_v2") is None for gene in panel["genes"])


def test_resolve_panel_from_symbols_preserves_unknown_symbols_with_warning(client) -> None:
    response = client.post(
        "/api/v1/panels/resolve",
        json={"symbols": ["brca1", "newgene", "BRCA1"]},
    )

    assert response.status_code == 200
    panel = response.json()
    assert panel["source"] == "custom"
    assert [gene["symbol"] for gene in panel["genes"]] == ["BRCA1", "NEWGENE"]
    unknown = panel["genes"][1]
    assert unknown["warnings"] == ["symbol_not_in_local_launch_catalog"]
    assert "HGNC alias normalization" in panel["warnings"][1]


def test_resolve_panel_from_known_mondo_seed(client) -> None:
    response = client.post(
        "/api/v1/panels/resolve",
        json={"disease_mondo": "MONDO:0019200"},
    )

    assert response.status_code == 200
    panel = response.json()
    assert panel["slug"] == "inherited-retinal-disease"
    assert "resolved by local MONDO seed mapping" in panel["warnings"]


def test_unknown_panel_slug_returns_404(client) -> None:
    response = client.get("/api/v1/panels/not-a-panel")

    assert response.status_code == 404


def test_panel_route_fails_closed_when_runtime_service_is_missing(client) -> None:
    del client.app.state.panel_service

    response = client.get("/api/v1/panels")

    assert response.status_code == 503
    assert response.json()["detail"] == "Panel service is unavailable."
