from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

from observability.incidents.incident_service import (
    create_experiment_incident,
    load_active_experiment,
    mark_experiment_running,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INCOMING_DIRECTORY = PROJECT_ROOT / "data" / "incoming"

REQUIRED_TRANSACTIONAL_ENTITIES = [
    "orders",
    "order_items",
    "payments",
    "shipments",
    "inventory",
]

MINIMUM_DAILY_ORDERS = 20
MAXIMUM_DAILY_ORDERS = 200


def expected_file_paths(
    batch_date: str,
) -> dict[str, Path]:
    return {
        entity_name: (
            INCOMING_DIRECTORY
            / f"{entity_name}_{batch_date}.csv"
        )
        for entity_name in REQUIRED_TRANSACTIONAL_ENTITIES
    }


def check_required_files(
    experiment: dict[str, Any],
) -> bool:
    batch_date = experiment["batch_date"]
    expected_files = expected_file_paths(batch_date)

    missing_entities = [
        entity_name
        for entity_name, file_path in expected_files.items()
        if not file_path.exists()
    ]

    if not missing_entities:
        return True

    create_experiment_incident(
        experiment=experiment,
        detection_layer="pre_ingestion",
        title="Expected source file missing",
        description=(
            f"Batch {batch_date} is missing required "
            f"entities: {missing_entities}."
        ),
        failed_rule="required_batch_files",
        evidence={
            "batch_date": batch_date,
            "missing_entities": missing_entities,
            "expected_files": {
                entity: str(file_path)
                for entity, file_path in expected_files.items()
            },
        },
        affected_entity=",".join(missing_entities),
        affected_table="raw",
    )

    return False


def check_order_volume(
    experiment: dict[str, Any],
) -> bool:
    batch_date = experiment["batch_date"]

    order_file = (
        INCOMING_DIRECTORY
        / f"orders_{batch_date}.csv"
    )

    if not order_file.exists():
        return False

    orders = pd.read_csv(order_file)
    order_count = len(orders)

    if (
        MINIMUM_DAILY_ORDERS
        <= order_count
        <= MAXIMUM_DAILY_ORDERS
    ):
        return True

    create_experiment_incident(
        experiment=experiment,
        detection_layer="pre_ingestion",
        title="Daily order-volume anomaly detected",
        description=(
            f"Order volume {order_count} is outside the "
            f"expected range {MINIMUM_DAILY_ORDERS}-"
            f"{MAXIMUM_DAILY_ORDERS}."
        ),
        failed_rule="daily_order_volume_range",
        evidence={
            "batch_date": batch_date,
            "actual_order_count": order_count,
            "minimum_expected": MINIMUM_DAILY_ORDERS,
            "maximum_expected": MAXIMUM_DAILY_ORDERS,
            "source_file": order_file.name,
        },
        affected_entity="orders",
        affected_table="raw.orders",
    )

    return False


def main() -> int:
    experiment = load_active_experiment()

    if experiment is None:
        print(
            "No active failure experiment. "
            "Pre-ingestion checks passed."
        )
        return 0

    mark_experiment_running(
        experiment["experiment_id"]
    )

    required_files_passed = check_required_files(
        experiment
    )

    if not required_files_passed:
        print("Required-file check failed.")
        return 1

    volume_check_passed = check_order_volume(
        experiment
    )

    if not volume_check_passed:
        print("Order-volume check failed.")
        return 1

    print("Pre-ingestion checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


