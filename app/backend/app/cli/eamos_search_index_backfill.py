from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from app.core.config import Settings
from app.core.db import build_session_factory, initialize_database
from app.repos.reports_repo import ReportsRepo
from app.repos.run_repo import RunRepo
from app.repos.search_repo import SearchRepo
from app.services.search_index import SearchIndexService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.eamos_search_index_backfill",
        description=(
            "Dry-run or apply a run/report search-index backfill from the existing "
            "Eamos database. This does not fetch sources, mutate Supabase, or run at startup."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write planned search index rows; default is dry-run only",
    )
    parser.add_argument(
        "--owner-user-id",
        help=(
            "optional owner to assign to backfilled private rows; omit to keep rows "
            "ownerless and hidden from user-facing private search until ownership is resolved"
        ),
    )
    parser.add_argument(
        "--clinical-release-files",
        action="store_true",
        help=(
            "also plan/index public condition and gene-disease rows from tracked "
            "MONDO/HPO/ClinGen/GenCC clinical source assets"
        ),
    )
    parser.add_argument(
        "--clinical-source-asset-root",
        type=Path,
        default=None,
        help=(
            "override the staged clinical source asset root for --clinical-release-files; "
            "defaults to app/backend/data/source_assets"
        ),
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit single-line JSON",
    )
    return parser


def run_backfill(
    *,
    apply: bool = False,
    owner_user_id: str | None = None,
    include_clinical_source_assets: bool = False,
    clinical_source_asset_root: Path | None = None,
    settings: Settings | None = None,
) -> dict[str, object]:
    resolved_settings = settings or Settings(jwt_secret="search-index-backfill-local")
    session_factory = build_session_factory(resolved_settings.database_url)
    initialize_database(session_factory)
    reports_repo = ReportsRepo(session_factory)
    run_repo = RunRepo(session_factory)
    search_repo = SearchRepo(session_factory)
    service = SearchIndexService(search_repo, reports_repo, run_repo)
    return service.backfill_reports_and_runs(
        dry_run=not apply,
        owner_user_id=owner_user_id,
        include_clinical_source_assets=include_clinical_source_assets,
        clinical_source_asset_root=clinical_source_asset_root,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_backfill(
        apply=bool(args.apply),
        owner_user_id=(args.owner_user_id or None),
        include_clinical_source_assets=bool(args.clinical_release_files),
        clinical_source_asset_root=args.clinical_source_asset_root,
    )
    indent = None if args.compact else 2
    print(json.dumps(result, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
