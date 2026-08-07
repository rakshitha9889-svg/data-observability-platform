from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_EXPERIMENT_PATH = (
    PROJECT_ROOT
    / "observability"
    / "incidents"
    / "active_experiment.json"
)


def create_database_engine() -> Engine:
    load_dotenv(PROJECT_ROOT / ".env")

    database_url = os.environ["DATABASE_URL"]

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def load_active_experiment() -> dict[str, Any] | None:
    if not ACTIVE_EXPERIMENT_PATH.exists():
        return None

    with ACTIVE_EXPERIMENT_PATH.open(
        "r",
        encoding="utf-8",
    ) as experiment_file:
        return json.load(experiment_file)


def mark_experiment_running(
    experiment_id: str,
) -> None:
    engine = create_database_engine()

    statement = text(
        """
        UPDATE observability.failure_experiments
        SET status = 'running',
            started_at = COALESCE(
                started_at,
                CURRENT_TIMESTAMP
            )
        WHERE experiment_id = :experiment_id
          AND status = 'prepared'
        """
    )

    with engine.begin() as connection:
        connection.execute(
            statement,
            {"experiment_id": experiment_id},
        )

    engine.dispose()


def incident_exists(
    engine: Engine,
    experiment_id: str,
) -> bool:
    statement = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM observability.incidents
            WHERE experiment_id = :experiment_id
        )
        """
    )

    with engine.connect() as connection:
        return bool(
            connection.execute(
                statement,
                {"experiment_id": experiment_id},
            ).scalar_one()
        )


def create_experiment_incident(
    *,
    experiment: dict[str, Any],
    detection_layer: str,
    title: str,
    description: str,
    failed_rule: str,
    evidence: dict[str, Any],
    affected_entity: str | None = None,
    affected_table: str | None = None,
) -> UUID | None:
    engine = create_database_engine()
    experiment_id = experiment["experiment_id"]

    if incident_exists(engine, experiment_id):
        print(
            "An incident already exists for experiment "
            f"{experiment_id}."
        )
        engine.dispose()
        return None

    insert_incident = text(
        """
        INSERT INTO observability.incidents (
            experiment_id,
            incident_type,
            severity,
            status,
            source,
            affected_entity,
            affected_table,
            title,
            description,
            failed_rule,
            evidence
        )
        VALUES (
            :experiment_id,
            'data_quality',
            :severity,
            'open',
            :source,
            :affected_entity,
            :affected_table,
            :title,
            :description,
            :failed_rule,
            CAST(:evidence AS JSONB)
        )
        RETURNING incident_id
        """
    )

    update_experiment = text(
        """
        UPDATE observability.failure_experiments
        SET status = 'detected',
            detected = TRUE,
            actual_detection_layer = :detection_layer,
            detected_at = CURRENT_TIMESTAMP,
            completed_at = CURRENT_TIMESTAMP,
            time_to_detection_seconds = EXTRACT(
                EPOCH FROM (
                    CURRENT_TIMESTAMP
                    - COALESCE(started_at, prepared_at)
                )
            )
        WHERE experiment_id = :experiment_id
        """
    )

    with engine.begin() as connection:
        incident_id = connection.execute(
            insert_incident,
            {
                "experiment_id": experiment_id,
                "severity": experiment["severity"],
                "source": detection_layer,
                "affected_entity": affected_entity,
                "affected_table": affected_table,
                "title": title,
                "description": description,
                "failed_rule": failed_rule,
                "evidence": json.dumps(
                    evidence,
                    default=str,
                ),
            },
        ).scalar_one()

        connection.execute(
            update_experiment,
            {
                "experiment_id": experiment_id,
                "detection_layer": detection_layer,
            },
        )

    engine.dispose()

    print(f"Incident created: {incident_id}")
    print(f"Detection layer: {detection_layer}")

    return incident_id