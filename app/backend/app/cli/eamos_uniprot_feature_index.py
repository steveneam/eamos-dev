from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.services.protein_annotation import resolve_protein_runtime_path, write_uniprot_feature_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact local UniProtKB/Swiss-Prot protein feature JSONL index."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="UniProt Swiss-Prot flatfile path; defaults to configured uniprot_sprot.dat.gz",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSONL path; defaults to configured protein feature index path",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    args = parser.parse_args(argv)

    settings = Settings(jwt_secret="uniprot-feature-index-local")
    input_path = args.input or resolve_protein_runtime_path(
        settings,
        settings.protein_annotation_uniprot_dat_path,
    )
    output_path = args.output or resolve_protein_runtime_path(
        settings,
        settings.protein_annotation_uniprot_feature_index_path,
    )

    summary = write_uniprot_feature_index(input_path, output_path)
    payload = {
        "status": "ok",
        "input": str(input_path),
        "output": str(output_path),
        **summary,
    }
    if args.compact:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
