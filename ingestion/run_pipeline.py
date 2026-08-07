from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from uuid import UUID

import pandas as pd
import structlog
from sqlalchemy import Engine

from ingestion.config import load_settings
from ingestion.database import (
    complete_file,
    complete_pipeline_run,
    create_database_engine,
    create_pipeline_run,
    file_checksum_exists,
    load_quarantine_records,
    load_raw_records,
    prepare_raw_records,
    register_file,
    update_archived_path,
)
from ingestion.file_utils import (
    SourceFile,
    archive_source_file,
    discover_source_files,
    move_rejected_file,
)
from ingestion.logging_config import configure_logging
from ingestion.validation import (
    FileSchemaError,
    validate_dataframe,
)

PIPELINE_NAME = "ecommerce_file_ingestion"


def create_empty_statistics() -> dict[str, int]:
    return {
        "files_processed": 0,
        "files_succeeded": 0,
        "files_failed": 0,
        "files_skipped": 0,
        "rows_received": 0,
        "rows_loaded": 0,
        "rows_rejected": 0,
    }


def determine_pipeline_batch_date(
    source_files: list[SourceFile],
) -> date | None:
    batch_dates = [
        source_file.batch_date
        for source_file in source_files
        if source_file.batch_date is not None
    ]

    if not batch_dates:
        return None

    return min(batch_dates)


def read_source_file(source_file: SourceFile) -> pd.DataFrame:
    return pd.read_csv(
        source_file.path,
        keep_default_na=True,
    )


def reject_invalid_filename(
    invalid_file: Path,
    rejected_directory: Path,
    logger: structlog.typing.FilteringBoundLogger,
) -> None:
    rejected_path = move_rejected_file(
        invalid_file,
        rejected_directory,
    )

    logger.error(
        "invalid_filename_rejected",
        source_file=invalid_file.name,
        rejected_path=str(rejected_path),
    )


def process_source_file(
    engine: Engine,
    run_id: UUID,
    source_file: SourceFile,
    archive_directory: Path,
    statistics: dict[str, int],
    logger: structlog.typing.FilteringBoundLogger,
) -> bool:
    file_logger = logger.bind(
        run_id=str(run_id),
        source_file=source_file.path.name,
        entity_name=source_file.entity_name,
        checksum=source_file.checksum,
    )

    with engine.connect() as connection:
        if file_checksum_exists(
            connection,
            source_file.entity_name,
            source_file.checksum,
        ):
            statistics["files_skipped"] += 1

            file_logger.warning(
                "duplicate_file_skipped",
            )

            return True

    dataframe = read_source_file(source_file)

    validation_result = validate_dataframe(
        dataframe,
        source_file.entity_name,
    )

    statistics["rows_received"] += (
        validation_result.received_count
    )

    with engine.begin() as connection:
        file_id = register_file(
            connection=connection,
            run_id=run_id,
            entity_name=source_file.entity_name,
            source_file=source_file.path.name,
            checksum=source_file.checksum,
            batch_date=source_file.batch_date,
            file_size_bytes=source_file.size_bytes,
            row_count=validation_result.received_count,
        )

        raw_records = prepare_raw_records(
            dataframe=validation_result.valid_records,
            run_id=run_id,
            source_file=source_file.path.name,
            checksum=source_file.checksum,
            batch_date=source_file.batch_date,
        )

        load_raw_records(
            connection=connection,
            entity_name=source_file.entity_name,
            dataframe=raw_records,
        )

        load_quarantine_records(
            connection=connection,
            run_id=run_id,
            file_id=file_id,
            entity_name=source_file.entity_name,
            source_file=source_file.path.name,
            failures=validation_result.invalid_records,
        )

        complete_file(
            connection=connection,
            file_id=file_id,
            loaded_count=validation_result.valid_count,
            rejected_count=validation_result.invalid_count,
        )

    archived_path = archive_source_file(
        source_file,
        archive_directory,
    )

    update_archived_path(
        engine=engine,
        file_id=file_id,
        archived_path=str(archived_path),
    )

    statistics["files_processed"] += 1
    statistics["files_succeeded"] += 1
    statistics["rows_loaded"] += validation_result.valid_count
    statistics["rows_rejected"] += (
        validation_result.invalid_count
    )

    file_logger.info(
        "file_processed",
        rows_received=validation_result.received_count,
        rows_loaded=validation_result.valid_count,
        rows_rejected=validation_result.invalid_count,
        archived_path=str(archived_path),
    )

    return True


def main() -> int:
    settings = load_settings()
    configure_logging(settings.log_level)

    logger = structlog.get_logger(
        pipeline_name=PIPELINE_NAME
    )

    settings.incoming_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings.archive_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings.rejected_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_files, invalid_files = discover_source_files(
        settings.incoming_directory
    )

    statistics = create_empty_statistics()
    statistics["files_failed"] = len(invalid_files)

    for invalid_file in invalid_files:
        reject_invalid_filename(
            invalid_file,
            settings.rejected_directory,
            logger,
        )

    if not source_files:
        logger.warning(
            "no_supported_source_files_found",
            incoming_directory=str(
                settings.incoming_directory
            ),
        )

        return 1 if invalid_files else 0

    engine = create_database_engine(
        settings.database_url
    )

    run_id = create_pipeline_run(
        engine=engine,
        pipeline_name=PIPELINE_NAME,
        batch_date=determine_pipeline_batch_date(source_files),
        files_discovered=len(source_files) + len(invalid_files),
    )

    logger = logger.bind(run_id=str(run_id))

    logger.info(
        "pipeline_started",
        files_discovered=len(source_files),
        invalid_files=len(invalid_files),
    )

    error_messages = []

    for source_file in source_files:
        try:
            process_source_file(
                engine=engine,
                run_id=run_id,
                source_file=source_file,
                archive_directory=settings.archive_directory,
                statistics=statistics,
                logger=logger,
            )
        except FileSchemaError as exception:
            statistics["files_processed"] += 1
            statistics["files_failed"] += 1

            rejected_path = move_rejected_file(
                source_file.path,
                settings.rejected_directory,
            )

            error_message = (
                f"{source_file.path.name}: {exception}"
            )
            error_messages.append(error_message)

            logger.error(
                "file_schema_validation_failed",
                source_file=source_file.path.name,
                entity_name=source_file.entity_name,
                error=str(exception),
                rejected_path=str(rejected_path),
            )
        except Exception as exception:
            statistics["files_processed"] += 1
            statistics["files_failed"] += 1

            error_message = (
                f"{source_file.path.name}: {exception}"
            )
            error_messages.append(error_message)

            logger.exception(
                "file_processing_failed",
                source_file=source_file.path.name,
                entity_name=source_file.entity_name,
                error=str(exception),
            )

    if statistics["files_failed"] > 0:
        if statistics["files_succeeded"] > 0:
            final_status = "partially_succeeded"
        else:
            final_status = "failed"
    else:
        final_status = "succeeded"

    complete_pipeline_run(
        engine=engine,
        run_id=run_id,
        status=final_status,
        statistics=statistics,
        error_type=(
            "FileProcessingError"
            if error_messages
            else None
        ),
        error_message=(
            " | ".join(error_messages)
            if error_messages
            else None
        ),
    )

    engine.dispose()

    logger.info(
        "pipeline_completed",
        status=final_status,
        **statistics,
    )

    return 1 if statistics["files_failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())