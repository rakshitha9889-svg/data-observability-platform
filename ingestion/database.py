from __future__ import annotations

import json
from datetime import date
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy import Engine, create_engine, text


def create_database_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def create_pipeline_run(
    engine: Engine,
    pipeline_name: str,
    batch_date: date | None,
    files_discovered: int,
) -> UUID:
    statement = text(
        """
        INSERT INTO observability.pipeline_runs (
            pipeline_name,
            batch_date,
            status,
            files_discovered
        )
        VALUES (
            :pipeline_name,
            :batch_date,
            'running',
            :files_discovered
        )
        RETURNING run_id
        """
    )

    with engine.begin() as connection:
        run_id = connection.execute(
            statement,
            {
                "pipeline_name": pipeline_name,
                "batch_date": batch_date,
                "files_discovered": files_discovered,
            },
        ).scalar_one()

    return run_id


def file_checksum_exists(
    connection: Any,
    entity_name: str,
    checksum: str,
) -> bool:
    statement = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM observability.ingested_files
            WHERE entity_name = :entity_name
              AND file_checksum = :checksum
              AND status = 'succeeded'
        )
        """
    )

    return bool(
        connection.execute(
            statement,
            {
                "entity_name": entity_name,
                "checksum": checksum,
            },
        ).scalar_one()
    )


def register_file(
    connection: Any,
    run_id: UUID,
    entity_name: str,
    source_file: str,
    checksum: str,
    batch_date: date | None,
    file_size_bytes: int,
    row_count: int,
) -> UUID:
    statement = text(
        """
        INSERT INTO observability.ingested_files (
            run_id,
            entity_name,
            source_file,
            file_checksum,
            batch_date,
            file_size_bytes,
            row_count,
            status
        )
        VALUES (
            :run_id,
            :entity_name,
            :source_file,
            :file_checksum,
            :batch_date,
            :file_size_bytes,
            :row_count,
            'processing'
        )
        RETURNING file_id
        """
    )

    return connection.execute(
        statement,
        {
            "run_id": run_id,
            "entity_name": entity_name,
            "source_file": source_file,
            "file_checksum": checksum,
            "batch_date": batch_date,
            "file_size_bytes": file_size_bytes,
            "row_count": row_count,
        },
    ).scalar_one()


def prepare_raw_records(
    dataframe: pd.DataFrame,
    run_id: UUID,
    source_file: str,
    checksum: str,
    batch_date: date | None,
) -> pd.DataFrame:
    raw_records = dataframe.copy()

    raw_records.rename(
        columns={
            "_source_row_number": "source_row_number",
        },
        inplace=True,
    )

    raw_records["source_file"] = source_file
    raw_records["file_checksum"] = checksum
    raw_records["batch_date"] = batch_date
    raw_records["run_id"] = str(run_id)

    metadata_columns = {
        "source_file",
        "file_checksum",
        "batch_date",
        "source_row_number",
        "run_id",
    }

    source_columns = [
        column
        for column in raw_records.columns
        if column not in metadata_columns
    ]

    raw_records["record_hash"] = raw_records[
        source_columns
    ].apply(calculate_record_hash, axis=1)

    return raw_records


def calculate_record_hash(row: pd.Series) -> str:
    import hashlib

    normalized_values = []

    for value in row.tolist():
        if pd.isna(value):
            normalized_values.append("")
        elif isinstance(value, pd.Timestamp):
            normalized_values.append(value.isoformat())
        else:
            normalized_values.append(str(value))

    record_content = "|".join(normalized_values)

    return hashlib.sha256(
        record_content.encode("utf-8")
    ).hexdigest()


def load_raw_records(
    connection: Any,
    entity_name: str,
    dataframe: pd.DataFrame,
) -> None:
    if dataframe.empty:
        return

    dataframe.to_sql(
        name=entity_name,
        con=connection,
        schema="raw",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )


def load_quarantine_records(
    connection: Any,
    run_id: UUID,
    file_id: UUID,
    entity_name: str,
    source_file: str,
    failures: list[Any],
) -> None:
    if not failures:
        return

    statement = text(
        """
        INSERT INTO quarantine.invalid_records (
            run_id,
            file_id,
            entity_name,
            source_file,
            source_row_number,
            failed_rule,
            failure_type,
            failure_reason,
            severity,
            record_data
        )
        VALUES (
            :run_id,
            :file_id,
            :entity_name,
            :source_file,
            :source_row_number,
            :failed_rule,
            :failure_type,
            :failure_reason,
            'medium',
            CAST(:record_data AS JSONB)
        )
        """
    )

    parameters = [
        {
            "run_id": run_id,
            "file_id": file_id,
            "entity_name": entity_name,
            "source_file": source_file,
            "source_row_number": failure.row_number,
            "failed_rule": failure.failed_rule,
            "failure_type": failure.failure_type,
            "failure_reason": failure.failure_reason,
            "record_data": json.dumps(
                failure.record_data,
                default=str,
            ),
        }
        for failure in failures
    ]

    connection.execute(statement, parameters)


def complete_file(
    connection: Any,
    file_id: UUID,
    loaded_count: int,
    rejected_count: int,
) -> None:
    if loaded_count == 0 and rejected_count > 0:
        status = "rejected"
    else:
        status = "succeeded"

    statement = text(
        """
        UPDATE observability.ingested_files
        SET status = :status,
            loaded_row_count = :loaded_count,
            rejected_row_count = :rejected_count,
            ingestion_completed_at = CURRENT_TIMESTAMP
        WHERE file_id = :file_id
        """
    )

    connection.execute(
        statement,
        {
            "file_id": file_id,
            "status": status,
            "loaded_count": loaded_count,
            "rejected_count": rejected_count,
        },
    )


def update_archived_path(
    engine: Engine,
    file_id: UUID,
    archived_path: str,
) -> None:
    statement = text(
        """
        UPDATE observability.ingested_files
        SET archived_path = :archived_path
        WHERE file_id = :file_id
        """
    )

    with engine.begin() as connection:
        connection.execute(
            statement,
            {
                "file_id": file_id,
                "archived_path": archived_path,
            },
        )


def complete_pipeline_run(
    engine: Engine,
    run_id: UUID,
    status: str,
    statistics: dict[str, int],
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    statement = text(
        """
        UPDATE observability.pipeline_runs
        SET status = :status,
            completed_at = CURRENT_TIMESTAMP,
            files_processed = :files_processed,
            files_succeeded = :files_succeeded,
            files_failed = :files_failed,
            files_skipped = :files_skipped,
            rows_received = :rows_received,
            rows_loaded = :rows_loaded,
            rows_rejected = :rows_rejected,
            error_type = :error_type,
            error_message = :error_message
        WHERE run_id = :run_id
        """
    )

    parameters = {
        "run_id": run_id,
        "status": status,
        "error_type": error_type,
        "error_message": error_message,
        **statistics,
    }

    with engine.begin() as connection:
        connection.execute(statement, parameters)