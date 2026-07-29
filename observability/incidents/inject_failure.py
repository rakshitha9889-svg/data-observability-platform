from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = (
    PROJECT_ROOT
    / "configs"
    / "failure_scenarios.yaml"
)

GENERATED_DIRECTORY = PROJECT_ROOT / "data" / "generated"
INCOMING_DIRECTORY = PROJECT_ROOT / "data" / "incoming"

ACTIVE_EXPERIMENT_PATH = (
    PROJECT_ROOT
    / "observability"
    / "incidents"
    / "active_experiment.json"
)

TRANSACTIONAL_ENTITIES = [
    "orders",
    "order_items",
    "payments",
    "shipments",
    "inventory",
]


def load_configuration() -> dict[str, Any]:
    with CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as config_file:
        return yaml.safe_load(config_file)


def ensure_incoming_directory_is_empty() -> None:
    existing_files = sorted(
        INCOMING_DIRECTORY.glob("*.csv")
    )

    if existing_files:
        filenames = [
            file_path.name
            for file_path in existing_files
        ]

        raise RuntimeError(
            "The incoming directory must contain no CSV files "
            "before preparing an experiment. Existing files: "
            f"{filenames}"
        )


def copy_clean_batch(batch_date: str) -> dict[str, Path]:
    copied_files = {}

    for entity_name in TRANSACTIONAL_ENTITIES:
        filename = f"{entity_name}_{batch_date}.csv"

        source_path = (
            GENERATED_DIRECTORY
            / entity_name
            / filename
        )

        destination_path = (
            INCOMING_DIRECTORY
            / filename
        )

        if not source_path.exists():
            raise FileNotFoundError(
                f"Generated source file not found: {source_path}"
            )

        shutil.copy2(
            source_path,
            destination_path,
        )

        copied_files[entity_name] = destination_path

    return copied_files


def read_csv(file_path: Path) -> pd.DataFrame:
    return pd.read_csv(
        file_path,
        keep_default_na=True,
    )


def write_csv(
    dataframe: pd.DataFrame,
    file_path: Path,
) -> None:
    dataframe.to_csv(
        file_path,
        index=False,
        encoding="utf-8",
        date_format="%Y-%m-%d %H:%M:%S",
    )


def inject_missing_payments_file(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    payment_file = copied_files["payments"]
    payment_file.unlink()

    return {
        "affected_file": payment_file.name,
        "change": "Deleted the expected payment file.",
    }


def inject_duplicate_order_id(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    order_file = copied_files["orders"]
    orders = read_csv(order_file)

    duplicated_order_id = orders.iloc[0]["order_id"]

    orders = pd.concat(
        [
            orders,
            orders.iloc[[0]],
        ],
        ignore_index=True,
    )

    write_csv(orders, order_file)

    return {
        "affected_file": order_file.name,
        "affected_value": duplicated_order_id,
        "change": "Duplicated the first order record.",
    }


def inject_null_customer_id(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    order_file = copied_files["orders"]
    orders = read_csv(order_file)

    affected_order_id = orders.loc[0, "order_id"]
    orders.loc[0, "customer_id"] = None

    write_csv(orders, order_file)

    return {
        "affected_file": order_file.name,
        "affected_value": affected_order_id,
        "change": "Set the first customer_id to null.",
    }


def inject_unknown_customer_id(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    order_file = copied_files["orders"]
    orders = read_csv(order_file)

    affected_order_id = orders.loc[0, "order_id"]
    orders.loc[0, "customer_id"] = "CUST_DOES_NOT_EXIST"

    write_csv(orders, order_file)

    return {
        "affected_file": order_file.name,
        "affected_value": affected_order_id,
        "change": (
            "Replaced customer_id with an unknown customer."
        ),
    }


def inject_negative_payment(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    payment_file = copied_files["payments"]
    payments = read_csv(payment_file)

    affected_payment_id = payments.loc[0, "payment_id"]
    payments.loc[0, "amount"] = -500.00

    write_csv(payments, payment_file)

    return {
        "affected_file": payment_file.name,
        "affected_value": affected_payment_id,
        "change": "Set the first payment amount to -500.00.",
    }


def inject_removed_order_column(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    order_file = copied_files["orders"]
    orders = read_csv(order_file)

    orders = orders.drop(columns=["customer_id"])

    write_csv(orders, order_file)

    return {
        "affected_file": order_file.name,
        "affected_value": "customer_id",
        "change": "Removed the customer_id column.",
    }


def inject_order_volume_drop(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    order_file = copied_files["orders"]
    item_file = copied_files["order_items"]
    payment_file = copied_files["payments"]
    shipment_file = copied_files["shipments"]

    orders = read_csv(order_file)
    original_order_count = len(orders)

    reduced_orders = orders.head(5).copy()

    retained_order_ids = set(
        reduced_orders["order_id"]
    )

    order_items = read_csv(item_file)
    payments = read_csv(payment_file)
    shipments = read_csv(shipment_file)

    order_items = order_items[
        order_items["order_id"].isin(retained_order_ids)
    ].copy()

    payments = payments[
        payments["order_id"].isin(retained_order_ids)
    ].copy()

    shipments = shipments[
        shipments["order_id"].isin(retained_order_ids)
    ].copy()

    write_csv(reduced_orders, order_file)
    write_csv(order_items, item_file)
    write_csv(payments, payment_file)
    write_csv(shipments, shipment_file)

    return {
        "affected_file": order_file.name,
        "original_order_count": original_order_count,
        "injected_order_count": len(reduced_orders),
        "change": "Reduced the batch to five orders.",
    }


def inject_excessive_delivery_delay(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    shipment_file = copied_files["shipments"]
    shipments = read_csv(shipment_file)

    expected_date = pd.to_datetime(
        shipments.loc[0, "expected_delivery_date"]
    )

    actual_date = expected_date + pd.Timedelta(days=30)

    affected_shipment_id = shipments.loc[
        0,
        "shipment_id",
    ]

    shipments.loc[
        0,
        "actual_delivery_date",
    ] = actual_date.strftime("%Y-%m-%d")

    shipments.loc[0, "status"] = "delayed"

    write_csv(shipments, shipment_file)

    return {
        "affected_file": shipment_file.name,
        "affected_value": affected_shipment_id,
        "change": (
            "Set actual delivery to 30 days after "
            "the expected delivery date."
        ),
    }


def inject_invalid_order_status(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    order_file = copied_files["orders"]
    orders = read_csv(order_file)

    affected_order_id = orders.loc[0, "order_id"]
    orders.loc[0, "status"] = "UNKNOWN_STATUS"

    write_csv(orders, order_file)

    return {
        "affected_file": order_file.name,
        "affected_value": affected_order_id,
        "change": "Set an unsupported order status.",
    }


def inject_order_total_mismatch(
    copied_files: dict[str, Path],
) -> dict[str, Any]:
    order_file = copied_files["orders"]
    orders = read_csv(order_file)

    affected_order_id = orders.loc[0, "order_id"]

    original_total = float(
        orders.loc[0, "order_total"]
    )

    injected_total = round(
        original_total + 100.00,
        2,
    )

    orders.loc[0, "order_total"] = injected_total

    write_csv(orders, order_file)

    return {
        "affected_file": order_file.name,
        "affected_value": affected_order_id,
        "original_total": original_total,
        "injected_total": injected_total,
        "change": "Added 100.00 to the order total.",
    }


INJECTION_FUNCTIONS = {
    "missing_payments_file": inject_missing_payments_file,
    "duplicate_order_id": inject_duplicate_order_id,
    "null_customer_id": inject_null_customer_id,
    "unknown_customer_id": inject_unknown_customer_id,
    "negative_payment": inject_negative_payment,
    "removed_order_column": inject_removed_order_column,
    "order_volume_drop": inject_order_volume_drop,
    "excessive_delivery_delay": (
        inject_excessive_delivery_delay
    ),
    "invalid_order_status": inject_invalid_order_status,
    "order_total_mismatch": inject_order_total_mismatch,
}


def register_experiment(
    scenario_name: str,
    scenario: dict[str, Any],
) -> UUID:
    load_dotenv(PROJECT_ROOT / ".env")

    import os

    database_url = os.environ["DATABASE_URL"]

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    statement = text(
        """
        INSERT INTO observability.failure_experiments (
            scenario_name,
            batch_date,
            expected_detection_layer,
            expected_severity,
            status,
            notes
        )
        VALUES (
            :scenario_name,
            :batch_date,
            :expected_detection_layer,
            :expected_severity,
            'prepared',
            :notes
        )
        RETURNING experiment_id
        """
    )

    with engine.begin() as connection:
        experiment_id = connection.execute(
            statement,
            {
                "scenario_name": scenario_name,
                "batch_date": scenario["batch_date"],
                "expected_detection_layer": (
                    scenario["expected_detection_layer"]
                ),
                "expected_severity": scenario["severity"],
                "notes": scenario["description"],
            },
        ).scalar_one()

    engine.dispose()

    return experiment_id


def save_active_experiment(
    experiment_id: UUID,
    scenario_name: str,
    scenario: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    experiment_record = {
        "experiment_id": str(experiment_id),
        "scenario_name": scenario_name,
        "batch_date": scenario["batch_date"],
        "expected_detection_layer": (
            scenario["expected_detection_layer"]
        ),
        "severity": scenario["severity"],
        "description": scenario["description"],
        "injection_evidence": evidence,
    }

    with ACTIVE_EXPERIMENT_PATH.open(
        "w",
        encoding="utf-8",
    ) as experiment_file:
        json.dump(
            experiment_record,
            experiment_file,
            indent=2,
        )


def prepare_experiment(scenario_name: str) -> None:
    configuration = load_configuration()
    scenarios = configuration["scenarios"]

    if scenario_name not in scenarios:
        raise ValueError(
            f"Unknown scenario: {scenario_name}. "
            f"Available scenarios: {sorted(scenarios)}"
        )

    ensure_incoming_directory_is_empty()

    scenario = scenarios[scenario_name]
    batch_date = scenario["batch_date"]

    copied_files = copy_clean_batch(batch_date)

    injection_function = INJECTION_FUNCTIONS[
        scenario_name
    ]

    evidence = injection_function(copied_files)

    experiment_id = register_experiment(
        scenario_name,
        scenario,
    )

    save_active_experiment(
        experiment_id,
        scenario_name,
        scenario,
        evidence,
    )

    print("Failure experiment prepared.")
    print(f"Experiment ID: {experiment_id}")
    print(f"Scenario: {scenario_name}")
    print(f"Batch date: {batch_date}")
    print(
        "Expected detection layer: "
        f"{scenario['expected_detection_layer']}"
    )
    print(f"Evidence: {evidence}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a reproducible data-quality "
            "failure experiment."
        )
    )

    parser.add_argument(
        "--scenario",
        required=True,
        choices=sorted(INJECTION_FUNCTIONS),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    prepare_experiment(arguments.scenario)


if __name__ == "__main__":
    main()


