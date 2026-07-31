CREATE OR REPLACE VIEW observability.vw_pipeline_reliability AS
SELECT
    run_id,
    pipeline_name,
    batch_date,
    status,
    started_at,
    completed_at,
    ROUND(
        EXTRACT(
            EPOCH FROM (completed_at - started_at)
        )::NUMERIC,
        2
    ) AS duration_seconds,
    files_discovered,
    files_processed,
    files_succeeded,
    files_failed,
    files_skipped,
    rows_received,
    rows_loaded,
    rows_rejected,
    CASE
        WHEN rows_received > 0
        THEN ROUND(
            100.0 * rows_rejected / rows_received,
            2
        )
        ELSE 0
    END AS rejection_rate_percentage,
    error_type,
    error_message
FROM observability.pipeline_runs;


CREATE OR REPLACE VIEW observability.vw_quality_trends AS
SELECT
    DATE(executed_at) AS execution_date,
    COALESCE(table_name, entity_name, 'unknown') AS affected_table,
    test_type,
    severity,
    status,
    COUNT(*) AS test_count,
    SUM(COALESCE(records_checked, 0)) AS records_checked,
    SUM(COALESCE(records_failed, 0)) AS records_failed,
    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE LOWER(status) = 'passed'
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS pass_rate_percentage
FROM observability.quality_test_results
GROUP BY
    DATE(executed_at),
    COALESCE(table_name, entity_name, 'unknown'),
    test_type,
    severity,
    status;


    CREATE OR REPLACE VIEW observability.vw_incident_management AS
SELECT
    incident_id,
    incident_type,
    severity,
    status,
    source,
    affected_entity,
    affected_table,
    title,
    failed_rule,
    suspected_cause,
    resolution_notes,
    detected_at,
    acknowledged_at,
    resolved_at,
    ROUND(
        EXTRACT(
            EPOCH FROM (
                acknowledged_at - detected_at
            )
        )::NUMERIC / 60.0,
        2
    ) AS time_to_acknowledge_minutes,
    ROUND(
        EXTRACT(
            EPOCH FROM (
                resolved_at - detected_at
            )
        )::NUMERIC / 60.0,
        2
    ) AS resolution_minutes,
    CASE
        WHEN LOWER(status) = 'open'
        THEN ROUND(
            EXTRACT(
                EPOCH FROM (
                    CURRENT_TIMESTAMP - detected_at
                )
            )::NUMERIC / 60.0,
            2
        )
        ELSE NULL
    END AS current_age_minutes
FROM observability.incidents;

CREATE OR REPLACE VIEW observability.vw_incident_impact AS
SELECT
    incident.incident_id,
    incident.title AS incident_title,
    incident.incident_type,
    incident.severity,
    incident.status AS incident_status,
    incident.detected_at,
    asset.unique_name AS impacted_asset,
    asset.asset_type,
    asset.database_name,
    asset.schema_name,
    asset.object_name,
    asset.owner_name,
    impact.impact_depth,
    impact.impact_path,
    CASE
        WHEN LOWER(asset.asset_type) IN (
            'kpi',
            'metric',
            'dashboard'
        )
        THEN TRUE
        ELSE FALSE
    END AS business_asset_affected
FROM observability.incident_impacted_assets AS impact
JOIN observability.incidents AS incident
    ON incident.incident_id = impact.incident_id
JOIN observability.lineage_assets AS asset
    ON asset.asset_id = impact.asset_id;

CREATE OR REPLACE VIEW observability.vw_failure_detection AS
SELECT
    experiment_id,
    scenario_name,
    batch_date,
    expected_detection_layer,
    expected_severity,
    status,
    detected,
    actual_detection_layer,
    prepared_at,
    started_at,
    detected_at,
    completed_at,
    time_to_detection_seconds,
    notes
FROM observability.failure_experiments;

CREATE OR REPLACE VIEW observability.vw_platform_summary AS
SELECT
    pipeline.total_pipeline_runs,
    pipeline.successful_pipeline_runs,
    pipeline.pipeline_success_rate_percentage,
    pipeline.latest_pipeline_completion,
    pipeline.freshness_hours,
    quality.total_quality_tests,
    quality.passed_quality_tests,
    quality.failed_quality_tests,
    quality.test_pass_rate_percentage,
    incidents.open_incidents,
    incidents.resolved_incidents,
    incidents.mttr_minutes,
    experiments.total_experiments,
    experiments.detected_experiments,
    experiments.detection_rate_percentage
FROM
(
    SELECT
        COUNT(*) AS total_pipeline_runs,

        COUNT(*) FILTER (
            WHERE LOWER(status) = 'succeeded'
        ) AS successful_pipeline_runs,

        ROUND(
            100.0
            * COUNT(*) FILTER (
                WHERE LOWER(status) = 'succeeded'
            )
            / NULLIF(COUNT(*), 0),
            2
        ) AS pipeline_success_rate_percentage,

        MAX(completed_at) AS latest_pipeline_completion,

        ROUND(
            EXTRACT(
                EPOCH FROM (
                    CURRENT_TIMESTAMP - MAX(completed_at)
                )
            )::NUMERIC / 3600.0,
            2
        ) AS freshness_hours
    FROM observability.pipeline_runs
) AS pipeline
CROSS JOIN
(
    SELECT
        COUNT(*) AS total_quality_tests,

        COUNT(*) FILTER (
            WHERE LOWER(status) = 'passed'
        ) AS passed_quality_tests,

        COUNT(*) FILTER (
            WHERE LOWER(status) = 'failed'
        ) AS failed_quality_tests,

        ROUND(
            100.0
            * COUNT(*) FILTER (
                WHERE LOWER(status) = 'passed'
            )
            / NULLIF(COUNT(*), 0),
            2
        ) AS test_pass_rate_percentage
    FROM observability.quality_test_results
) AS quality
CROSS JOIN
(
    SELECT
        COUNT(*) FILTER (
            WHERE LOWER(status) = 'open'
        ) AS open_incidents,

        COUNT(*) FILTER (
            WHERE LOWER(status) = 'resolved'
        ) AS resolved_incidents,

        ROUND(
            AVG(
                EXTRACT(
                    EPOCH FROM (
                        resolved_at - detected_at
                    )
                )
            ) FILTER (
                WHERE resolved_at IS NOT NULL
                  AND detected_at IS NOT NULL
            )::NUMERIC / 60.0,
            2
        ) AS mttr_minutes
    FROM observability.incidents
) AS incidents
CROSS JOIN
(
    SELECT
        COUNT(*) AS total_experiments,

        COUNT(*) FILTER (
            WHERE detected IS TRUE
        ) AS detected_experiments,

        ROUND(
            100.0
            * COUNT(*) FILTER (
                WHERE detected IS TRUE
            )
            / NULLIF(COUNT(*), 0),
            2
        ) AS detection_rate_percentage
    FROM observability.failure_experiments
) AS experiments;