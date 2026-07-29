from __future__ import annotations

import argparse
from uuid import UUID

from sqlalchemy import text

from observability.lineage.impact_analysis import (
    calculate_downstream_impact,
)
from observability.lineage.load_lineage import (
    create_database_engine,
)


def link_incident_impact(
    incident_id: UUID,
    asset_name: str,
) -> int:
    impacted_assets = calculate_downstream_impact(
        asset_name
    )

    statement = text(
        """
        INSERT INTO observability.incident_impacted_assets (
            incident_id,
            asset_id,
            impact_depth,
            impact_path
        )
        VALUES (
            :incident_id,
            :asset_id,
            :impact_depth,
            :impact_path
        )
        ON CONFLICT (incident_id, asset_id)
        DO UPDATE SET
            impact_depth = EXCLUDED.impact_depth,
            impact_path = EXCLUDED.impact_path,
            recorded_at = CURRENT_TIMESTAMP
        """
    )

    engine = create_database_engine()

    with engine.begin() as connection:
        for asset in impacted_assets:
            connection.execute(
                statement,
                {
                    "incident_id": incident_id,
                    "asset_id": asset[
                        "impacted_asset_id"
                    ],
                    "impact_depth": asset[
                        "impact_depth"
                    ],
                    "impact_path": asset[
                        "impact_path"
                    ],
                },
            )

    engine.dispose()

    return len(impacted_assets)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--incident-id",
        required=True,
        type=UUID,
    )

    parser.add_argument(
        "--asset",
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    impacted_count = link_incident_impact(
        arguments.incident_id,
        arguments.asset,
    )

    print(
        f"Linked {impacted_count} downstream assets "
        f"to incident {arguments.incident_id}."
    )


if __name__ == "__main__":
    main()