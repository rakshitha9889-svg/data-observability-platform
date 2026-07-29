from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import text

from observability.incidents.incident_service import (
    ACTIVE_EXPERIMENT_PATH,
    create_database_engine,
    load_active_experiment,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INCOMING_DIRECTORY = PROJECT_ROOT / "data" / "incoming"

EXPERIMENT_ARCHIVE_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "archive"
    / "experiments"
)

EXPERIMENT_HISTORY_DIRECTORY = (
    PROJECT_ROOT
    / "observability"
    / "incidents"
    / "history"
)

RAW_TRANSACTIONAL_TABLES = [
    "order_items",
    "payments",
    "shipments",
    "inventory",
    "orders",
]


def archive_remaining_source_files(
    experiment: dict[str, Any],
) -> list[str]:
    experiment_id = experiment["experiment_id"]
    scenario_name = experiment["scenario_name"]
    batch_date = experiment["batch_date"]

    destination_directory = (
        EXPERIMENT_ARCHIVE_DIRECTORY
        / scenario_name
        / experiment_id
    )

    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    archived_files = []

    for source_file in INCOMING_DIRECTORY.glob(
        f"*_{batch_date}.csv"
    ):
        destination_path = (
            destination_directory / source_file.name
        )

        shutil.move(
            str(source_file),
            str(destination_path),
        )

        archived_files.append(
            str(destination_path)
        )

    return archived_files


def delete_experimental_raw_rows(
    experiment: dict[str, Any],
) -> dict[str, int]:
    batch_date = experiment["batch_date"]
    deleted_counts = {}

    engine = create_database_engine()

    with engine.begin() as connection:
        for table_name in RAW_TRANSACTIONAL_TABLES:
            result = connection.execute(
                text(
                    f"""
                    DELETE FROM raw.{table_name}
                    WHERE batch_date = :batch_date
                    """
                ),
                {"batch_date": batch_date},
            )

            deleted_counts[table_name] = result.rowcount

    engine.dispose()

    return deleted_counts


def resolve_experiment_incident(
    experiment: dict[str, Any],
    deleted_counts: dict[str, int],
    archived_files: list[str],
) -> None:
    experiment_id = experiment["experiment_id"]

    resolution_evidence = json.dumps(
        {
            "deleted_raw_rows": deleted_counts,
            "archived_remaining_files": archived_files,
        }
    )

    engine = create_database_engine()

    update_incident = text(
        """
        UPDATE observability.incidents
        SET status = 'resolved',
            resolved_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            resolution_notes = (
                'Experimental source rows removed and '
                'the clean analytical baseline restored. '
                || :resolution_evidence
            )
        WHERE experiment_id = :experiment_id
          AND status <> 'resolved'
        """
    )

    update_experiment = text(
        """
        UPDATE observability.failure_experiments
        SET status = 'completed',
            completed_at = CURRENT_TIMESTAMP,
            notes = COALESCE(notes, '')
                || ' Experiment evidence preserved and '
                || 'experimental source rows cleaned.'
        WHERE experiment_id = :experiment_id
        """
    )

    with engine.begin() as connection:
        connection.execute(
            update_incident,
            {
                "experiment_id": experiment_id,
                "resolution_evidence": (
                    resolution_evidence
                ),
            },
        )

        connection.execute(
            update_experiment,
            {"experiment_id": experiment_id},
        )

    engine.dispose()


def preserve_experiment_manifest(
    experiment: dict[str, Any],
) -> Path:
    EXPERIMENT_HISTORY_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    history_path = (
        EXPERIMENT_HISTORY_DIRECTORY
        / f"{experiment['experiment_id']}.json"
    )

    shutil.move(
        str(ACTIVE_EXPERIMENT_PATH),
        str(history_path),
    )

    return history_path


def main() -> None:
    experiment = load_active_experiment()

    if experiment is None:
        raise RuntimeError(
            "No active experiment is available to complete."
        )

    archived_files = archive_remaining_source_files(
        experiment
    )

    deleted_counts = delete_experimental_raw_rows(
        experiment
    )

    resolve_experiment_incident(
        experiment,
        deleted_counts,
        archived_files,
    )

    history_path = preserve_experiment_manifest(
        experiment
    )

    print("Experiment cleanup completed.")
    print(
        f"Scenario: {experiment['scenario_name']}"
    )
    print(f"Deleted rows: {deleted_counts}")
    print(
        f"Remaining files archived: {len(archived_files)}"
    )
    print(f"Manifest preserved: {history_path}")


if __name__ == "__main__":
    main()