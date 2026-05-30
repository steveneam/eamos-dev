from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"

CREATE_POLICY_RE = re.compile(
    r"""
    create\s+policy\s+"(?P<name>[^"]+)"\s+
    on\s+(?P<table>[\w.]+)\s+
    for\s+(?P<command>select|insert|update|delete)\s+
    (?P<body>.*?)
    ;
    """,
    flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
)
DROP_POLICY_RE = re.compile(
    r"""
    drop\s+policy\s+if\s+exists\s+"(?P<name>[^"]+)"\s+
    on\s+(?P<table>[\w.]+)\s*
    ;
    """,
    flags=re.IGNORECASE | re.DOTALL | re.VERBOSE,
)
WRAPPED_AUTH_UID_RE = re.compile(r"\(\s*select\s+auth\.uid\s*\(\s*\)\s*\)", flags=re.IGNORECASE)
AUTH_UID_RE = re.compile(r"auth\.uid\s*\(\s*\)", flags=re.IGNORECASE)


@dataclass(frozen=True)
class Policy:
    name: str
    table: str
    command: str
    body: str

    @property
    def signature(self) -> tuple[str, str]:
        return (self.table.lower(), self.command.lower())


def _migration_sql(name: str) -> str:
    return (MIGRATIONS_DIR / name).read_text(encoding="utf-8")


def _created_policies(sql: str) -> dict[str, Policy]:
    policies: dict[str, Policy] = {}
    for match in CREATE_POLICY_RE.finditer(sql):
        policy = Policy(
            name=match.group("name"),
            table=match.group("table"),
            command=match.group("command"),
            body=match.group("body"),
        )
        policies[policy.name] = policy
    return policies


def _dropped_policy_targets(sql: str) -> set[tuple[str, str]]:
    return {
        (match.group("name"), match.group("table").lower())
        for match in DROP_POLICY_RE.finditer(sql)
    }


def test_supabase_rls_initplan_migration_recreates_existing_auth_uid_policies() -> None:
    initial = _created_policies(_migration_sql("0001_submission_ledger.sql"))
    optimized = _created_policies(_migration_sql("0007_optimize_rls_auth_uid_initplan.sql"))
    auth_uid_policy_names = {
        name for name, policy in initial.items() if AUTH_UID_RE.search(policy.body)
    }

    assert len(auth_uid_policy_names) == 7
    assert set(optimized) == auth_uid_policy_names
    assert {name: optimized[name].signature for name in optimized} == {
        name: initial[name].signature for name in auth_uid_policy_names
    }


def test_supabase_rls_initplan_migration_wraps_auth_uid_in_policy_predicates() -> None:
    optimized_sql = _migration_sql("0007_optimize_rls_auth_uid_initplan.sql")
    optimized = _created_policies(optimized_sql)
    dropped_targets = _dropped_policy_targets(optimized_sql)

    assert len(dropped_targets) == len(optimized) == 7
    assert dropped_targets == {(policy.name, policy.table.lower()) for policy in optimized.values()}

    for policy in optimized.values():
        unwrapped_body = WRAPPED_AUTH_UID_RE.sub("", policy.body)
        assert not AUTH_UID_RE.search(unwrapped_body), policy.name
        assert WRAPPED_AUTH_UID_RE.search(policy.body), policy.name


def test_supabase_rls_profile_update_policy_preserves_new_row_ownership_check() -> None:
    policy = _created_policies(_migration_sql("0007_optimize_rls_auth_uid_initplan.sql"))[
        "Allow users to modify their own profile data fields"
    ]

    body = re.sub(r"\s+", " ", policy.body.lower())

    assert "using ((select auth.uid()) = id)" in body
    assert "with check ((select auth.uid()) = id)" in body


def test_protein_annotation_cache_migration_is_backend_only_private_schema() -> None:
    sql = _migration_sql("0008_protein_annotation_metadata_cache.sql")
    normalized = re.sub(r"\s+", " ", sql.lower())

    assert "create schema if not exists eamos_private" in normalized
    assert "public.protein_annotation" not in normalized
    assert "storage.buckets" not in normalized
    assert "enable row level security" in normalized
    assert "grant usage on schema eamos_private to service_role" in normalized
    assert "grant select, insert, update, delete on eamos_private.protein_annotation_cache" in (
        normalized
    )
    assert "to anon" not in normalized
    assert "to authenticated" not in normalized
    assert "protein_accession" in normalized
    assert "uniprot_release" in normalized


def test_local_model_cache_migration_is_backend_only_private_schema() -> None:
    sql = _migration_sql("0009_local_model_cache_perimeter.sql")
    normalized = re.sub(r"\s+", " ", sql.lower())

    assert "create schema if not exists eamos_private" in normalized
    assert "create table if not exists eamos_private.local_source_versions" in normalized
    assert "create table if not exists eamos_private.local_model_cache_entries" in normalized
    assert "create table if not exists eamos_private.local_model_jobs" in normalized
    assert "storage.buckets" not in normalized
    assert "public.local_model_cache" not in normalized
    assert "enable row level security" in normalized
    assert "revoke all on all tables in schema eamos_private from anon" in normalized
    assert "revoke all on all tables in schema eamos_private from authenticated" in normalized
    assert "grant select, insert, update, delete on eamos_private.local_model_cache_entries" in (
        normalized
    )
    assert "to service_role" in normalized
    assert "to anon" not in normalized
    assert "to authenticated" not in normalized
    assert "restricted_fields_stripped boolean not null default true" in normalized
    assert "public_serialization_policy text not null default 'backend_only_private_cache'" in (
        normalized
    )


def test_private_cache_advisor_hardening_uses_deny_all_browser_policies() -> None:
    sql = _migration_sql("0010_private_cache_advisor_hardening.sql")
    normalized = re.sub(r"\s+", " ", sql.lower())

    private_tables = (
        "protein_annotation_source_versions",
        "protein_annotation_jobs",
        "protein_annotation_cache",
        "local_source_versions",
        "local_model_cache_entries",
        "local_model_jobs",
    )
    for table in private_tables:
        assert f"on eamos_private.{table}" in normalized

    assert normalized.count("as restrictive for all to anon, authenticated using (false)") == 6
    assert normalized.count("with check (false)") == 6
    assert "using (true)" not in normalized
    assert "with check (true)" not in normalized
    assert "idx_protein_annotation_jobs_user_id" in normalized
    assert "idx_local_model_jobs_result_cache_id" in normalized


def test_private_clinical_source_tables_are_backend_only_relational_sources() -> None:
    sql = _migration_sql("0011_private_clinical_source_tables.sql")
    normalized = re.sub(r"\s+", " ", sql.lower())

    private_tables = (
        "clinical_mondo_diseases",
        "clinical_hpo_terms",
        "clinical_hpo_disease_phenotypes",
        "clinical_hpo_gene_phenotypes",
        "clinical_clingen_gene_validity",
        "clinical_gencc_assertions",
    )
    for table in private_tables:
        assert f"create table if not exists eamos_private.{table}" in normalized
        assert f"alter table eamos_private.{table} enable row level security" in normalized
        assert f"grant select, insert, update, delete on eamos_private.{table}" in normalized
        assert f"on eamos_private.{table}" in normalized

    assert "public.clinical_" not in normalized
    assert "storage.buckets" not in normalized
    assert "revoke all on all tables in schema eamos_private from anon" in normalized
    assert "revoke all on all tables in schema eamos_private from authenticated" in normalized
    assert normalized.count("as restrictive for all to anon, authenticated using (false)") == 6
    assert normalized.count("with check (false)") == 6
    assert "using (true)" not in normalized
    assert "with check (true)" not in normalized
    assert (
        normalized.count("references eamos_private.local_source_versions(source_version_id)") == 6
    )
    assert "idx_clinical_mondo_diseases_xrefs_gin" in normalized
    assert "idx_clinical_hpo_disease_phenotypes_unique" in normalized
    assert "idx_clinical_clingen_gene_validity_unique" in normalized
    assert "idx_clinical_gencc_assertions_unique" in normalized


def test_private_source_asset_storage_metadata_blocks_public_access() -> None:
    sql = _migration_sql("0012_private_source_asset_storage_metadata.sql")
    normalized = re.sub(r"\s+", " ", sql.lower())

    private_tables = (
        "source_asset_objects",
        "source_asset_materializations",
    )
    for table in private_tables:
        assert f"create table if not exists eamos_private.{table}" in normalized
        assert f"alter table eamos_private.{table} enable row level security" in normalized
        assert f"grant select, insert, update, delete on eamos_private.{table}" in normalized
        assert f"on eamos_private.{table}" in normalized

    assert "storage.buckets" not in normalized
    assert "create policy" in normalized
    assert "revoke all on all tables in schema eamos_private from anon" in normalized
    assert "revoke all on all tables in schema eamos_private from authenticated" in normalized
    assert normalized.count("as restrictive for all to anon, authenticated using (false)") == 2
    assert normalized.count("with check (false)") == 2
    assert "public_access_allowed boolean not null default false" in normalized
    assert "frontend_direct_access_allowed boolean not null default false" in normalized
    assert "public_access_allowed = false" in normalized
    assert "frontend_direct_access_allowed = false" in normalized
    assert "materialization_status <> 'ready' or verified_at is not null" in normalized
    assert "stale_allowed = false" in normalized
    assert "idx_source_asset_objects_unique_path" in normalized
    assert "idx_source_asset_materializations_unique_env_path" in normalized


def test_private_source_asset_bucket_is_private_and_bounded() -> None:
    sql = _migration_sql("20260530120018_private_source_asset_bucket.sql")
    normalized = re.sub(r"\s+", " ", sql.lower())

    assert "insert into storage.buckets" in normalized
    assert "'eamos-source-assets'" in normalized
    assert "public, file_size_limit, allowed_mime_types" in normalized
    assert "false, 1073741824" in normalized
    assert "array['application/octet-stream']::text[]" in normalized
    assert "on conflict (id)" in normalized
    assert "public = false" in normalized
    assert "create policy" not in normalized
    assert "using (true)" not in normalized
    assert "with check (true)" not in normalized
