from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import psycopg2


def normalize_database_url(database_url: str) -> str:
    return database_url.replace(
        "postgresql+psycopg2://",
        "postgresql://",
    )


def record_task_event(
    context: dict[str, Any],
    event_status: str,
) -> None:
    database_url = os.environ["DATABASE_URL"]
    task_instance = context["task_instance"]
    exception = context.get("exception")
    logical_date = context.get("logical_date")

    error_type = None
    error_message = None

    if exception is not None:
        error_type = type(exception).__name__
        error_message = str(exception)

    statement = """
        INSERT INTO observability.airflow_task_events (
            dag_id,
            task_id,
            dag_run_id,
            event_status,
            try_number,
            logical_date,
            event_time,
            error_type,
            error_message
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """

    values = (
        task_instance.dag_id,
        task_instance.task_id,
        context.get("run_id", "unknown"),
        event_status,
        task_instance.try_number,
        logical_date,
        datetime.now(timezone.utc),
        error_type,
        error_message,
    )

    with psycopg2.connect(
        normalize_database_url(database_url)
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, values)


def task_success_callback(
    context: dict[str, Any],
) -> None:
    record_task_event(context, "success")


def task_failure_callback(
    context: dict[str, Any],
) -> None:
    record_task_event(context, "failed")


def task_retry_callback(
    context: dict[str, Any],
) -> None:
    record_task_event(context, "retry")