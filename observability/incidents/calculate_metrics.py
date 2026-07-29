from __future__ import annotations

from pathlib import Path

import pandas as pd

from observability.incidents.incident_service import (
    create_database_engine,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESULTS_DIRECTORY = (
    PROJECT_ROOT / "docs" / "results"
)

CSV_OUTPUT_PATH = (
    RESULTS_DIRECTORY
    / "failure_experiment_results.csv"
)

MARKDOWN_OUTPUT_PATH = (
    RESULTS_DIRECTORY
    / "failure_experiment_results.md"
)


EXPERIMENT_QUERY = """
WITH ranked_experiments AS (
    SELECT
        scenario_name,
        batch_date,
        expected_detection_layer,
        expected_severity,
        detected,
        actual_detection_layer,
        time_to_detection_seconds,
        status,
        prepared_at,

        ROW_NUMBER() OVER (
            PARTITION BY scenario_name
            ORDER BY prepared_at DESC
        ) AS scenario_rank

    FROM observability.failure_experiments
)

SELECT
    scenario_name,
    batch_date,
    expected_detection_layer,
    actual_detection_layer,
    expected_severity,
    detected,
    time_to_detection_seconds,
    status

FROM ranked_experiments

WHERE scenario_rank = 1

ORDER BY scenario_name
"""


def format_markdown_table(
    dataframe: pd.DataFrame,
) -> str:
    columns = dataframe.columns.tolist()

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(
        ["---"] * len(columns)
    ) + " |"

    rows = []

    for _, row in dataframe.iterrows():
        values = [
            str(row[column]).replace("|", "\\|")
            for column in columns
        ]

        rows.append(
            "| " + " | ".join(values) + " |"
        )

    return "\n".join(
        [header, separator, *rows]
    )


def main() -> None:
    RESULTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    engine = create_database_engine()

    experiments = pd.read_sql(
        EXPERIMENT_QUERY,
        engine,
    )

    engine.dispose()

    total_experiments = len(experiments)
    detected_experiments = int(
        experiments["detected"].sum()
    )

    detection_rate = (
        detected_experiments / total_experiments
        if total_experiments
        else 0
    )

    detected_rows = experiments[
        experiments["detected"]
    ]

    average_detection_time = (
        detected_rows[
            "time_to_detection_seconds"
        ].mean()
        if not detected_rows.empty
        else 0
    )

    layer_accuracy = (
        experiments["expected_detection_layer"]
        == experiments["actual_detection_layer"]
    ).mean()

    experiments.to_csv(
        CSV_OUTPUT_PATH,
        index=False,
    )

    markdown = f"""# Failure Experiment Results

## Summary

- Total scenarios: {total_experiments}
- Detected scenarios: {detected_experiments}
- Detection rate: {detection_rate:.1%}
- Average time to detection: {average_detection_time:.3f} seconds
- Correct detection-layer rate: {layer_accuracy:.1%}

## Scenario results

{format_markdown_table(experiments)}
"""

    MARKDOWN_OUTPUT_PATH.write_text(
        markdown,
        encoding="utf-8",
    )

    print(f"Total scenarios: {total_experiments}")
    print(
        f"Detected scenarios: {detected_experiments}"
    )
    print(f"Detection rate: {detection_rate:.1%}")
    print(
        "Average time to detection: "
        f"{average_detection_time:.3f} seconds"
    )
    print(
        "Correct detection-layer rate: "
        f"{layer_accuracy:.1%}"
    )
    print(f"CSV results: {CSV_OUTPUT_PATH}")
    print(f"Markdown results: {MARKDOWN_OUTPUT_PATH}")


if __name__ == "__main__":
    main()