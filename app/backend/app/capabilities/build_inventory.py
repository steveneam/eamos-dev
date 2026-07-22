"""Create a deterministic, local-only runtime package and footprint inventory."""

from __future__ import annotations

import argparse
from importlib.metadata import distributions
import json
from pathlib import Path
from typing import Iterable

INVENTORY_SCHEMA_VERSION = "runtime_component_inventory.v1"
SCIENTIFIC_DISTRIBUTIONS = {
    "biopython",
    "primer3-py",
    "pypdf",
    "pypdfium2",
    "pysam",
}


def build_inventory() -> dict[str, object]:
    packages: list[dict[str, object]] = []
    scientific_sizes: dict[str, int] = {}
    runtime_payload_size = 0
    for distribution in sorted(distributions(), key=lambda item: _name(item).lower()):
        name = _name(distribution)
        size_bytes = _distribution_size(distribution.files or ())
        runtime_payload_size += size_bytes
        normalized_name = name.lower()
        if normalized_name in SCIENTIFIC_DISTRIBUTIONS:
            scientific_sizes[normalized_name] = size_bytes
        packages.append(
            {
                "name": name,
                "version": distribution.version,
                "purl": f"pkg:pypi/{normalized_name}@{distribution.version}",
                "installed_size_bytes": size_bytes,
                "notice_files": _notice_files(distribution.files or ()),
            }
        )
    binary_sizes = {
        path.name: path.stat().st_size
        for path in (Path("/usr/bin/hmmscan"), Path("/usr/bin/hmmpress"))
        if path.is_file()
    }
    runtime_payload_size += sum(binary_sizes.values())
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "measurement": {
            "scope": "installed_python_distributions_and_declared_binaries",
            "runtime_payload_size_bytes": runtime_payload_size,
            "container_image_size_bytes": None,
            "container_image_size_requirement": (
                "record docker image inspect size and immutable digest after the image build"
            ),
        },
        "scientific_distribution_sizes_bytes": scientific_sizes,
        "binary_sizes_bytes": binary_sizes,
        "packages": packages,
    }


def write_inventory(output: Path) -> None:
    payload = json.dumps(build_inventory(), sort_keys=True, separators=(",", ":"))
    output.write_text(f"{payload}\n", encoding="utf-8")


def _name(distribution) -> str:
    return str(distribution.metadata.get("Name") or distribution.name)


def _distribution_size(files: Iterable[object]) -> int:
    total = 0
    for file in files:
        try:
            resolved = Path(file.locate())
            if resolved.is_file():
                total += resolved.stat().st_size
        except OSError:
            continue
    return total


def _notice_files(files: Iterable[object]) -> list[str]:
    markers = ("license", "notice", "copying", "copyright", "authors")
    return sorted(
        str(file) for file in files if any(marker in str(file).lower() for marker in markers)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_inventory(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
