from __future__ import annotations

import argparse
import json
from typing import Any

from sqlalchemy import text

from observability.lineage.load_lineage import (
    create_database_engine,
)

DOWNSTREAM_IMPACT_QUERY = text(
    """
    WITH RECURSIVE downstream_impact AS (
        SELECT
            upstream.asset_id AS source_asset_id,
            downstream.asset_id AS impacted_asset_id,
            downstream.unique_name,
            downstream.asset_type,
            downstream.owner_name,
            downstream.description,
            1 AS impact_depth,
            ARRAY[
                upstream.unique_name,
                downstream.unique_name
            ]::VARCHAR[] AS impact_path

        FROM observability.lineage_assets AS upstream

        JOIN observability.lineage_edges AS edge
            ON edge.upstream_asset_id = upstream.asset_id

        JOIN observability.lineage_assets AS downstream
            ON downstream.asset_id = edge.downstream_asset_id

        WHERE upstream.unique_name = :asset_name

        UNION ALL

        SELECT
            impact.source_asset_id,
            downstream.asset_id,
            downstream.unique_name,
            downstream.asset_type,
            downstream.owner_name,
            downstream.description,
            impact.impact_depth + 1,
            impact.impact_path || downstream.unique_name

        FROM downstream_impact AS impact

        JOIN observability.lineage_edges AS edge
            ON edge.upstream_asset_id
                = impact.impacted_asset_id

        JOIN observability.lineage_assets AS downstream
            ON downstream.asset_id
                = edge.downstream_asset_id

        WHERE NOT (
            downstream.unique_name
            = ANY(impact.impact_path)
        )
          AND impact.impact_depth < 20
    )

    SELECT DISTINCT ON (unique_name)
        impacted_asset_id,
        unique_name,
        asset_type,
        owner_name,
        description,
        impact_depth,
        array_to_string(
            impact_path,
            ' -> '
        ) AS impact_path

    FROM downstream_impact

    ORDER BY unique_name, impact_depth
    """
)


def find_asset(
    asset_name: str,
) -> dict[str, Any] | None:
    engine = create_database_engine()

    statement = text(
        """
        SELECT
            asset_id,
            unique_name,
            asset_type,
            database_name,
            schema_name,
            object_name,
            owner_name,
            description
        FROM observability.lineage_assets
        WHERE unique_name = :asset_name
        """
    )

    with engine.connect() as connection:
        asset = connection.execute(
            statement,
            {"asset_name": asset_name},
        ).mappings().one_or_none()

    engine.dispose()

    return dict(asset) if asset else None


def calculate_downstream_impact(
    asset_name: str,
) -> list[dict[str, Any]]:
    engine = create_database_engine()

    with engine.connect() as connection:
        impacted_assets = [
            dict(row)
            for row in connection.execute(
                DOWNSTREAM_IMPACT_QUERY,
                {"asset_name": asset_name},
            ).mappings()
        ]

    engine.dispose()

    return impacted_assets


def suggest_severity(
    impacted_assets: list[dict[str, Any]],
) -> str:
    impacted_types = {
        asset["asset_type"]
        for asset in impacted_assets
    }

    if "dashboard" in impacted_types:
        return "critical"

    if "kpi" in impacted_types:
        return "high"

    if "model" in impacted_types:
        return "medium"

    return "low"


def print_impact_report(
    source_asset: dict[str, Any],
    impacted_assets: list[dict[str, Any]],
) -> None:
    report = {
        "source_asset": source_asset,
        "impacted_asset_count": len(
            impacted_assets
        ),
        "suggested_severity": suggest_severity(
            impacted_assets
        ),
        "impacted_assets": impacted_assets,
    }

    print(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Return all downstream assets affected "
            "by a source or model failure."
        )
    )

    parser.add_argument(
        "--asset",
        required=True,
        help=(
            "Exact lineage asset unique name, for example "
            "source.data_observability.raw.payments"
        ),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    source_asset = find_asset(arguments.asset)

    if source_asset is None:
        raise ValueError(
            f"Lineage asset not found: {arguments.asset}"
        )

    impacted_assets = calculate_downstream_impact(
        arguments.asset
    )

    print_impact_report(
        source_asset,
        impacted_assets,
    )


if __name__ == "__main__":
    main()