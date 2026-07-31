#!/usr/bin/env bash

set -euo pipefail

OUTPUT_DIRECTORY="dashboard/tableau_data"

mkdir -p "${OUTPUT_DIRECTORY}"

docker compose exec -T postgres \
    psql -U commerce_user -d commerce \
    -c "\copy (
        SELECT *
        FROM observability.vw_platform_summary
    ) TO STDOUT WITH CSV HEADER" \
    > "${OUTPUT_DIRECTORY}/platform_summary.csv"

docker compose exec -T postgres \
    psql -U commerce_user -d commerce \
    -c "\copy (
        SELECT *
        FROM observability.vw_pipeline_reliability
        ORDER BY started_at
    ) TO STDOUT WITH CSV HEADER" \
    > "${OUTPUT_DIRECTORY}/pipeline_reliability.csv"

docker compose exec -T postgres \
    psql -U commerce_user -d commerce \
    -c "\copy (
        SELECT *
        FROM observability.vw_quality_trends
        ORDER BY execution_date
    ) TO STDOUT WITH CSV HEADER" \
    > "${OUTPUT_DIRECTORY}/quality_trends.csv"

docker compose exec -T postgres \
    psql -U commerce_user -d commerce \
    -c "\copy (
        SELECT *
        FROM observability.vw_incident_management
        ORDER BY detected_at
    ) TO STDOUT WITH CSV HEADER" \
    > "${OUTPUT_DIRECTORY}/incident_management.csv"

docker compose exec -T postgres \
    psql -U commerce_user -d commerce \
    -c "\copy (
        SELECT *
        FROM observability.vw_incident_impact
        ORDER BY detected_at, impact_depth
    ) TO STDOUT WITH CSV HEADER" \
    > "${OUTPUT_DIRECTORY}/incident_impact.csv"

docker compose exec -T postgres \
    psql -U commerce_user -d commerce \
    -c "\copy (
        SELECT *
        FROM observability.vw_failure_detection
        ORDER BY prepared_at
    ) TO STDOUT WITH CSV HEADER" \
    > "${OUTPUT_DIRECTORY}/failure_detection.csv"

echo "Tableau datasets exported successfully."