from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MANIFEST_PATH = (
    PROJECT_ROOT
    / "dbt_project"
    / "target"
    / "manifest.json"
)

BUSINESS_LINEAGE_PATH = (
    PROJECT_ROOT
    / "configs"
    / "business_lineage.yaml"
)

SUPPORTED_NODE_TYPES = {
    "model",
    "test",
}

SUPPORTED_RESOURCE_PREFIXES = (
    "model.",
    "test.",
    "source.",
)


def create_database_engine() -> Engine:
    load_dotenv(PROJECT_ROOT / ".env")

    return create_engine(
        os.environ["DATABASE_URL"],
        pool_pre_ping=True,
    )


def load_json(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required artifact not found: {file_path}"
        )

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        return json.load(input_file)


def load_yaml(file_path: Path) -> dict[str, Any]:
    with file_path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        return yaml.safe_load(input_file)


def upsert_asset(
    connection: Any,
    *,
    unique_name: str,
    asset_type: str,
    database_name: str | None,
    schema_name: str | None,
    object_name: str | None,
    owner_name: str | None,
    description: str | None,
    metadata: dict[str, Any],
) -> None:
    statement = text(
        """
        INSERT INTO observability.lineage_assets (
            unique_name,
            asset_type,
            database_name,
            schema_name,
            object_name,
            owner_name,
            description,
            metadata
        )
        VALUES (
            :unique_name,
            :asset_type,
            :database_name,
            :schema_name,
            :object_name,
            :owner_name,
            :description,
            CAST(:metadata AS JSONB)
        )
        ON CONFLICT (unique_name)
        DO UPDATE SET
            asset_type = EXCLUDED.asset_type,
            database_name = EXCLUDED.database_name,
            schema_name = EXCLUDED.schema_name,
            object_name = EXCLUDED.object_name,
            owner_name = EXCLUDED.owner_name,
            description = EXCLUDED.description,
            metadata = EXCLUDED.metadata,
            updated_at = CURRENT_TIMESTAMP
        """
    )

    connection.execute(
        statement,
        {
            "unique_name": unique_name,
            "asset_type": asset_type,
            "database_name": database_name,
            "schema_name": schema_name,
            "object_name": object_name,
            "owner_name": owner_name,
            "description": description,
            "metadata": json.dumps(
                metadata,
                default=str,
            ),
        },
    )


def get_owner_name(resource: dict[str, Any]) -> str | None:
    meta = resource.get("meta") or {}

    owner = meta.get("owner")

    if isinstance(owner, str):
        return owner

    group = resource.get("group")

    if isinstance(group, str):
        return group

    return None


def load_dbt_assets(
    connection: Any,
    manifest: dict[str, Any],
) -> int:
    asset_count = 0

    resources = {
        **manifest.get("sources", {}),
        **manifest.get("nodes", {}),
    }

    for unique_id, resource in resources.items():
        resource_type = resource.get("resource_type")

        if (
            resource_type not in SUPPORTED_NODE_TYPES
            and resource_type != "source"
        ):
            continue

        upsert_asset(
            connection,
            unique_name=unique_id,
            asset_type=resource_type,
            database_name=resource.get("database"),
            schema_name=resource.get("schema"),
            object_name=(
                resource.get("alias")
                or resource.get("name")
            ),
            owner_name=get_owner_name(resource),
            description=resource.get("description"),
            metadata={
                "package_name": resource.get(
                    "package_name"
                ),
                "path": resource.get("path"),
                "original_file_path": resource.get(
                    "original_file_path"
                ),
                "tags": resource.get("tags", []),
                "relation_name": resource.get(
                    "relation_name"
                ),
                "depends_on": resource.get(
                    "depends_on",
                    {},
                ),
            },
        )

        asset_count += 1

    return asset_count


def load_business_assets(
    connection: Any,
    business_lineage: dict[str, Any],
) -> int:
    for asset in business_lineage["assets"]:
        upsert_asset(
            connection,
            unique_name=asset["unique_name"],
            asset_type=asset["asset_type"],
            database_name=None,
            schema_name=None,
            object_name=asset["object_name"],
            owner_name=asset.get("owner_name"),
            description=asset.get("description"),
            metadata={
                "source": "business_lineage",
            },
        )

    return len(business_lineage["assets"])


def asset_exists(
    connection: Any,
    unique_name: str,
) -> bool:
    return bool(
        connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM observability.lineage_assets
                    WHERE unique_name = :unique_name
                )
                """
            ),
            {"unique_name": unique_name},
        ).scalar_one()
    )


def insert_edge(
    connection: Any,
    *,
    upstream: str,
    downstream: str,
    edge_type: str,
    source_system: str,
) -> bool:
    if not asset_exists(connection, upstream):
        return False

    if not asset_exists(connection, downstream):
        return False

    statement = text(
        """
        INSERT INTO observability.lineage_edges (
            upstream_asset_id,
            downstream_asset_id,
            edge_type,
            source_system
        )
        SELECT
            upstream.asset_id,
            downstream.asset_id,
            :edge_type,
            :source_system
        FROM observability.lineage_assets AS upstream
        CROSS JOIN observability.lineage_assets AS downstream
        WHERE upstream.unique_name = :upstream
          AND downstream.unique_name = :downstream
        ON CONFLICT DO NOTHING
        """
    )

    connection.execute(
        statement,
        {
            "upstream": upstream,
            "downstream": downstream,
            "edge_type": edge_type,
            "source_system": source_system,
        },
    )

    return True


def load_dbt_edges(
    connection: Any,
    manifest: dict[str, Any],
) -> int:
    edge_count = 0

    parent_map = manifest.get("parent_map", {})

    for downstream, upstream_nodes in parent_map.items():
        if not downstream.startswith(
            SUPPORTED_RESOURCE_PREFIXES
        ):
            continue

        for upstream in upstream_nodes:
            if not upstream.startswith(
                SUPPORTED_RESOURCE_PREFIXES
            ):
                continue

            if insert_edge(
                connection,
                upstream=upstream,
                downstream=downstream,
                edge_type="depends_on",
                source_system="dbt_manifest",
            ):
                edge_count += 1

    return edge_count


def load_business_edges(
    connection: Any,
    business_lineage: dict[str, Any],
) -> int:
    edge_count = 0

    for edge in business_lineage["edges"]:
        if insert_edge(
            connection,
            upstream=edge["upstream"],
            downstream=edge["downstream"],
            edge_type="feeds",
            source_system="business_mapping",
        ):
            edge_count += 1

    return edge_count


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    business_lineage = load_yaml(
        BUSINESS_LINEAGE_PATH
    )

    engine = create_database_engine()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE FROM observability.lineage_edges
                WHERE source_system IN (
                    'dbt_manifest',
                    'business_mapping'
                )
                """
            )
        )

        dbt_asset_count = load_dbt_assets(
            connection,
            manifest,
        )

        business_asset_count = load_business_assets(
            connection,
            business_lineage,
        )

        dbt_edge_count = load_dbt_edges(
            connection,
            manifest,
        )

        business_edge_count = load_business_edges(
            connection,
            business_lineage,
        )

    engine.dispose()

    print("Lineage loading completed.")
    print(f"dbt assets: {dbt_asset_count}")
    print(f"Business assets: {business_asset_count}")
    print(f"dbt edges: {dbt_edge_count}")
    print(f"Business edges: {business_edge_count}")


if __name__ == "__main__":
    main()