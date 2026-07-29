from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow.providers.standard.operators.bash import (
    BashOperator,
)
from airflow.sdk import DAG, task

from callbacks import (
    task_failure_callback,
    task_retry_callback,
    task_success_callback,
)


PROJECT_DIRECTORY = "/opt/airflow/project"
INCOMING_DIRECTORY = f"{PROJECT_DIRECTORY}/data/incoming"
DBT_DIRECTORY = f"{PROJECT_DIRECTORY}/dbt_project"


default_arguments = {
    "owner": "rakshitha",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=20),
    "on_success_callback": task_success_callback,
    "on_failure_callback": task_failure_callback,
    "on_retry_callback": task_retry_callback,
}


with DAG(
    dag_id="ecommerce_data_observability_pipeline",
    description=(
        "Ingest, transform and validate e-commerce data."
    ),
    default_args=default_arguments,
    start_date=datetime(
        2026,
        7,
        1,
        tzinfo=timezone.utc,
    ),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    tags=[
        "data-engineering",
        "data-quality",
        "observability",
    ],
) as dag:

    wait_for_source_files = BashOperator(
        task_id="wait_for_source_files",
        bash_command=f"""
            FILE_COUNT=$(find "{INCOMING_DIRECTORY}" \
                -maxdepth 1 \
                -type f \
                -name "*.csv" \
                | wc -l)

            echo "Source files discovered: $FILE_COUNT"

            if [ "$FILE_COUNT" -eq 0 ]; then
                echo "No source CSV files are available."
                exit 1
            fi
        """,
    )

    @task(task_id="validate_source_filenames")
    def validate_source_filenames() -> list[str]:
        import re

        incoming_directory = Path(INCOMING_DIRECTORY)

        valid_patterns = [
            re.compile(r"^(customers|products)\.csv$"),
            re.compile(
                r"^(orders|order_items|payments|"
                r"shipments|inventory)_"
                r"\d{4}-\d{2}-\d{2}\.csv$"
            ),
        ]

        source_files = sorted(
            incoming_directory.glob("*.csv")
        )

        invalid_filenames = [
            source_file.name
            for source_file in source_files
            if not any(
                pattern.fullmatch(source_file.name)
                for pattern in valid_patterns
            )
        ]

        if invalid_filenames:
            raise ValueError(
                "Invalid source filenames: "
                f"{invalid_filenames}"
            )

        filenames = [
            source_file.name
            for source_file in source_files
        ]

        print(f"Validated source files: {filenames}")

        return filenames

    load_raw_data = BashOperator(
        task_id="load_raw_data",
        bash_command=f"""
            cd "{PROJECT_DIRECTORY}"

            set +e
            python -m ingestion.run_pipeline
            INGESTION_EXIT_CODE=$?
            set -e

            python -m \
                observability.quality.detect_ingestion_incident

            exit $INGESTION_EXIT_CODE
        """,
    )

    run_dbt_models = BashOperator(
        task_id="run_dbt_models",
        bash_command=f"""
            cd "{DBT_DIRECTORY}"
            dbt run --profiles-dir .
        """,
    )

    run_dbt_tests_and_capture_results = BashOperator(
        task_id="run_dbt_tests_and_capture_results",
        bash_command=f"""
            cd "{DBT_DIRECTORY}"

            set +e
            dbt test --profiles-dir .
            DBT_EXIT_CODE=$?
            set -e

            cd "{PROJECT_DIRECTORY}"

            python -m \
                observability.quality.capture_dbt_results

            python -m \
                observability.quality.detect_dbt_incident

            exit $DBT_EXIT_CODE
        """,
    )
    notify_success = BashOperator(
        task_id="notify_success",
        bash_command="""
            echo "The e-commerce observability pipeline succeeded."
        """,
    )

    validated_files = validate_source_filenames()

    run_pre_ingestion_checks = BashOperator(
            task_id="run_pre_ingestion_checks",
            bash_command=f"""
                cd "{PROJECT_DIRECTORY}"
                python -m observability.quality.pre_ingestion_checks
            """,
        )

    (
        wait_for_source_files
        >> validated_files
        >> run_pre_ingestion_checks
        >> load_raw_data
        >> run_dbt_models
        >> run_dbt_tests_and_capture_results
        >> notify_success
    )

   