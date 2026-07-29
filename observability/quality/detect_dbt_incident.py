from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from observability.incidents.incident_service import (
    create_experiment_incident,
    load_active_experiment,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RUN_RESULTS_PATH = (
    PROJECT_ROOT
    / "dbt_project"
    / "target"
    / "run_results.json"
)

DBT_SCENARIOS = {
    "unknown_customer_id",
    "excessive_delivery_delay",
    "order_total_mismatch",
}


def load_failed_tests() -> list[dict[str, Any]]:
    if not RUN_RESULTS_PATH.exists():
        raise FileNotFoundError(
            f"dbt results not found: {RUN_RESULTS_PATH}"
        )

    with RUN_RESULTS_PATH.open(
        "r",
        encoding="utf-8",
    ) as results_file:
        run_results = json.load(results_file)

    return [
        result
        for result in run_results["results"]
        if result["unique_id"].startswith("test.")
        and result["status"] in {
            "fail",
            "error",
            "warn",
        }
    ]


def main() -> None:
    experiment = load_active_experiment()

    if experiment is None:
        print("No active failure experiment.")
        return

    scenario_name = experiment["scenario_name"]

    if scenario_name not in DBT_SCENARIOS:
        print(
            f"Scenario {scenario_name} is not expected "
            "at the dbt layer."
        )
        return

    failed_tests = load_failed_tests()

    if not failed_tests:
        print("No failed dbt tests were found.")
        return

    first_test = failed_tests[0]

    create_experiment_incident(
        experiment=experiment,
        detection_layer=experiment[
            "expected_detection_layer"
        ],
        title=f"dbt quality failure: {scenario_name}",
        description=(
            f"{len(failed_tests)} dbt quality test(s) "
            "failed for the active experiment."
        ),
        failed_rule=first_test["unique_id"],
        evidence={
            "failed_test_count": len(failed_tests),
            "failed_tests": failed_tests,
            "injection_evidence": experiment[
                "injection_evidence"
            ],
        },
        affected_entity="dbt",
        affected_table="analytics",
    )

    print("dbt incident detected.")


if __name__ == "__main__":
    main()