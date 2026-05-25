from __future__ import annotations

import json

from app.cli.eamos_search_input import main


def test_eamos_search_input_cli_prints_source_bundle_for_file(tmp_path, capsys) -> None:
    input_file = tmp_path / "variant-stack.txt"
    input_file.write_text(
        "\n".join(
            [
                "abca4:c.1622T>C",
                "8:140300616 T>G\t'chr' prefix is optional",
                "1-1042601-A-AGAGAG\tinsertion of GAGAG",
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["--fixture-mode", "--input-file", str(input_file)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "fixture"
    assert output["count"] == 3
    assert output["results"][0]["normalized"]["gene"] == "ABCA4"
    assert output["results"][0]["normalized"]["hgvs"] == "c.1622T>C"
    assert output["results"][1]["source_inputs"]["gnomad"] == "8-140300616-T-G"
    assert (
        output["results"][2]["source_inputs"]["clinvar"] == "NC_000001.11:g.1042601_1042602insGAGAG"
    )


def test_eamos_search_input_cli_accepts_unquoted_spaced_genomic_query(capsys) -> None:
    exit_code = main(["--fixture-mode", "6", "31740453", "G", "T"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    result = output["results"][0]
    assert result["normalized"]["kind"] == "genomic"
    assert result["source_inputs"]["gnomad"] == "6-31740453-G-T"
    assert result["source_inputs"]["variant_validator"] == "NC_000006.12:g.31740453G>T"


def test_eamos_search_input_cli_prints_rsid_candidates(capsys) -> None:
    exit_code = main(["--fixture-mode", "rs61752871"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    result = output["results"][0]
    assert result["normalized"]["kind"] == "rsid"
    assert result["rsid_candidates"][0]["gene"] == "RPE65"
    assert result["rsid_candidates"][0]["cdna"] == "c.271C>T"
    assert result["rsid_candidates"][0]["genomic_hg38"] == "1-68444858-G-A"
