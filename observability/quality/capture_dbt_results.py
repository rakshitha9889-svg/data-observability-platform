from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RUN_RESULTS_PATH = (
    PROJECT_ROOT
    / "dbt_project"
    / "target"
    / "run_results.json"
)


def normalize_status(status: str) -> str:
    status_mapping = {
        "pass": "passed",
        "success": "passed",
        "fail": "failed",
        "error": "error",
        "warn": "warning",
        "skipped": "skipped",
    }

    return status_mapping.get(status.lower(), "error")


def determine_test_type(unique_id: str) -> str:
    if "assert_" in unique_id:
        return "singular"

    return "generic"


def main() -> None:
    if not RUN_RESULTS_PATH.exists():
        raise FileNotFoundError(
            f"dbt artifact not found: {RUN_RESULTS_PATH}"
        )

    database_url = os.environ["DATABASE_URL"]

    with RUN_RESULTS_PATH.open(
        "r",
        encoding="utf-8",
    ) as results_file:
        run_results = json.load(results_file)

    test_results = [
        result
        for result in run_results["results"]
        if result["unique_id"].startswith("test.")
    ]

    insert_statement = text(
        """
        INSERT INTO observability.quality_test_results (
            test_name,
            test_type,
            entity_name,
            table_name,
            status,
            severity,
            records_checked,
            records_failed,
            failure_message,
            evidence
        )
        VALUES (
            :test_name,
            :test_type,
            :entity_name,
            :table_name,
            :status,
            :severity,
            :records_checked,
            :records_failed,
            :failure_message,
            CAST(:evidence AS JSONB)
        )
        """
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    with engine.begin() as connection:
        for result in test_results:
            failures = result.get("failures")

            if failures is None:
                failures = 0

            evidence = json.dumps(
                {
                    "unique_id": result["unique_id"],
                    "execution_time": result.get(
                        "execution_time"
                    ),
                    "adapter_response": result.get(
                        "adapter_response"
                    ),
                },
                default=str,
            )

            connection.execute(
                insert_statement,
                {
                    "test_name": result["unique_id"],
                    "test_type": determine_test_type(
                        result["unique_id"]
                    ),
                    "entity_name": "dbt",
                    "table_name": result["unique_id"],
                    "status": normalize_status(
                        result["status"]
                    ),
                    "severity": "high",
                    "records_checked": max(
                        int(failures),
                        0,
                    ),
                    "records_failed": max(
                        int(failures),
                        0,
                    ),
                    "failure_message": result.get(
                        "message"
                    ),
                    "evidence": evidence,
                },
            )

    engine.dispose()

    print(
        f"Captured {len(test_results)} dbt test results."
    )


if __name__ == "__main__":
    main()