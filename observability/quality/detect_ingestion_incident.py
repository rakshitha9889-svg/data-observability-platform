from __future__ import annotations

from typing import Any

from sqlalchemy import text

from observability.incidents.incident_service import (
    create_database_engine,
    create_experiment_incident,
    load_active_experiment,
)


INGESTION_SCENARIOS = {
    "duplicate_order_id",
    "null_customer_id",
    "negative_payment",
    "invalid_order_status",
}

SCHEMA_SCENARIOS = {
    "removed_order_column",
}


def find_quarantine_evidence(
    experiment: dict[str, Any],
) -> list[dict[str, Any]]:
    affected_file = experiment[
        "injection_evidence"
    ].get("affected_file")

    engine = create_database_engine()

    statement = text(
        """
        SELECT
            quarantine_id,
            entity_name,
            source_file,
            source_row_number,
            failed_rule,
            failure_reason,
            record_data,
            quarantined_at
        FROM quarantine.invalid_records
        WHERE source_file = :source_file
        ORDER BY quarantined_at DESC
        """
    )

    with engine.connect() as connection:
        evidence = [
            dict(row)
            for row in connection.execute(
                statement,
                {"source_file": affected_file},
            ).mappings()
        ]

    engine.dispose()

    return evidence


def find_schema_failure(
    experiment: dict[str, Any],
) -> dict[str, Any] | None:
    affected_file = experiment[
        "injection_evidence"
    ].get("affected_file")

    engine = create_database_engine()

    statement = text(
        """
        SELECT
            run_id,
            status,
            files_failed,
            error_type,
            error_message,
            started_at,
            completed_at
        FROM observability.pipeline_runs
        WHERE error_message ILIKE :filename_pattern
        ORDER BY started_at DESC
        LIMIT 1
        """
    )

    with engine.connect() as connection:
        result = connection.execute(
            statement,
            {
                "filename_pattern": (
                    f"%{affected_file}%"
                )
            },
        ).mappings().one_or_none()

    engine.dispose()

    if result is None:
        return None

    return dict(result)


def detect_quarantine_incident(
    experiment: dict[str, Any],
) -> bool:
    quarantine_evidence = find_quarantine_evidence(
        experiment
    )

    if not quarantine_evidence:
        return False

    first_failure = quarantine_evidence[0]

    create_experiment_incident(
        experiment=experiment,
        detection_layer="ingestion_validation",
        title=(
            f"Ingestion validation failure: "
            f"{experiment['scenario_name']}"
        ),
        description=(
            f"{len(quarantine_evidence)} invalid record(s) "
            "were quarantined before reaching raw tables."
        ),
        failed_rule=first_failure["failed_rule"],
        evidence={
            "quarantined_record_count": len(
                quarantine_evidence
            ),
            "records": quarantine_evidence[:10],
            "injection_evidence": experiment[
                "injection_evidence"
            ],
        },
        affected_entity=first_failure["entity_name"],
        affected_table=(
            f"raw.{first_failure['entity_name']}"
        ),
    )

    return True


def detect_schema_incident(
    experiment: dict[str, Any],
) -> bool:
    schema_failure = find_schema_failure(experiment)

    if schema_failure is None:
        return False

    create_experiment_incident(
        experiment=experiment,
        detection_layer="schema_validation",
        title="Source schema contract violation",
        description=(
            "The ingestion pipeline rejected a source "
            "file because its schema did not match "
            "the expected contract."
        ),
        failed_rule="required_columns",
        evidence={
            "pipeline_failure": schema_failure,
            "injection_evidence": experiment[
                "injection_evidence"
            ],
        },
        affected_entity="orders",
        affected_table="raw.orders",
    )

    return True


def main() -> None:
    experiment = load_active_experiment()

    if experiment is None:
        print("No active failure experiment.")
        return

    scenario_name = experiment["scenario_name"]

    if scenario_name in INGESTION_SCENARIOS:
        detected = detect_quarantine_incident(
            experiment
        )
    elif scenario_name in SCHEMA_SCENARIOS:
        detected = detect_schema_incident(
            experiment
        )
    else:
        print(
            f"Scenario {scenario_name} is not expected "
            "at the ingestion layer."
        )
        return

    if detected:
        print("Ingestion incident detected.")
    else:
        print(
            "No matching ingestion evidence was found."
        )


if __name__ == "__main__":
    main()