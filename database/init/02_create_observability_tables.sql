CREATE TABLE IF NOT EXISTS observability.pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    pipeline_name VARCHAR(150) NOT NULL,
    batch_date DATE,
    status VARCHAR(30) NOT NULL DEFAULT 'running',

    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    files_discovered INTEGER NOT NULL DEFAULT 0,
    files_processed INTEGER NOT NULL DEFAULT 0,
    files_succeeded INTEGER NOT NULL DEFAULT 0,
    files_failed INTEGER NOT NULL DEFAULT 0,
    files_skipped INTEGER NOT NULL DEFAULT 0,

    rows_received BIGINT NOT NULL DEFAULT 0,
    rows_loaded BIGINT NOT NULL DEFAULT 0,
    rows_rejected BIGINT NOT NULL DEFAULT 0,

    error_type VARCHAR(200),
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_pipeline_run_status
        CHECK (
            status IN (
                'running',
                'succeeded',
                'failed',
                'partially_succeeded',
                'skipped'
            )
        ),

    CONSTRAINT chk_pipeline_run_file_counts
        CHECK (
            files_discovered >= 0
            AND files_processed >= 0
            AND files_succeeded >= 0
            AND files_failed >= 0
            AND files_skipped >= 0
        ),

    CONSTRAINT chk_pipeline_run_row_counts
        CHECK (
            rows_received >= 0
            AND rows_loaded >= 0
            AND rows_rejected >= 0
        ),

    CONSTRAINT chk_pipeline_run_completion
        CHECK (
            completed_at IS NULL
            OR completed_at >= started_at
        )
);


CREATE TABLE IF NOT EXISTS observability.ingested_files (
    file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,

    entity_name VARCHAR(100) NOT NULL,
    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE,

    file_size_bytes BIGINT,
    row_count BIGINT NOT NULL DEFAULT 0,
    loaded_row_count BIGINT NOT NULL DEFAULT 0,
    rejected_row_count BIGINT NOT NULL DEFAULT 0,

    status VARCHAR(30) NOT NULL,
    ingestion_started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ingestion_completed_at TIMESTAMPTZ,

    archived_path VARCHAR(1000),
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ingested_files_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_ingested_file_checksum
        UNIQUE (entity_name, file_checksum),

    CONSTRAINT chk_ingested_file_status
        CHECK (
            status IN (
                'discovered',
                'processing',
                'succeeded',
                'failed',
                'rejected',
                'skipped_duplicate'
            )
        ),

    CONSTRAINT chk_ingested_file_counts
        CHECK (
            row_count >= 0
            AND loaded_row_count >= 0
            AND rejected_row_count >= 0
        ),

    CONSTRAINT chk_ingested_file_size
        CHECK (
            file_size_bytes IS NULL
            OR file_size_bytes >= 0
        )
);


CREATE TABLE IF NOT EXISTS observability.quality_test_results (
    test_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID,

    test_name VARCHAR(250) NOT NULL,
    test_type VARCHAR(100) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(200),
    column_name VARCHAR(200),

    status VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',

    records_checked BIGINT NOT NULL DEFAULT 0,
    records_failed BIGINT NOT NULL DEFAULT 0,

    failure_message TEXT,
    evidence JSONB,

    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_quality_test_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT chk_quality_test_status
        CHECK (
            status IN (
                'passed',
                'failed',
                'warning',
                'error',
                'skipped'
            )
        ),

    CONSTRAINT chk_quality_test_severity
        CHECK (
            severity IN (
                'critical',
                'high',
                'medium',
                'low'
            )
        ),

    CONSTRAINT chk_quality_test_counts
        CHECK (
            records_checked >= 0
            AND records_failed >= 0
            AND records_failed <= records_checked
        )
);


CREATE TABLE IF NOT EXISTS observability.incidents (
    incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID,
    test_result_id UUID,

    incident_type VARCHAR(150) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'open',

    source VARCHAR(150) NOT NULL,
    affected_entity VARCHAR(100),
    affected_table VARCHAR(200),

    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    failed_rule VARCHAR(500),
    evidence JSONB,

    suspected_cause TEXT,
    resolution_notes TEXT,

    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_incident_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT fk_incident_test_result
        FOREIGN KEY (test_result_id)
        REFERENCES observability.quality_test_results(test_result_id),

    CONSTRAINT chk_incident_severity
        CHECK (
            severity IN (
                'critical',
                'high',
                'medium',
                'low'
            )
        ),

    CONSTRAINT chk_incident_status
        CHECK (
            status IN (
                'open',
                'investigating',
                'resolved',
                'closed'
            )
        ),

    CONSTRAINT chk_incident_resolution_time
        CHECK (
            resolved_at IS NULL
            OR resolved_at >= detected_at
        )
);


CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON observability.pipeline_runs(status);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
    ON observability.pipeline_runs(started_at);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_batch_date
    ON observability.pipeline_runs(batch_date);

CREATE INDEX IF NOT EXISTS idx_ingested_files_run_id
    ON observability.ingested_files(run_id);

CREATE INDEX IF NOT EXISTS idx_ingested_files_entity
    ON observability.ingested_files(entity_name);

CREATE INDEX IF NOT EXISTS idx_ingested_files_status
    ON observability.ingested_files(status);

CREATE INDEX IF NOT EXISTS idx_quality_results_run_id
    ON observability.quality_test_results(run_id);

CREATE INDEX IF NOT EXISTS idx_quality_results_status
    ON observability.quality_test_results(status);

CREATE INDEX IF NOT EXISTS idx_incidents_run_id
    ON observability.incidents(run_id);

CREATE INDEX IF NOT EXISTS idx_incidents_status
    ON observability.incidents(status);

CREATE INDEX IF NOT EXISTS idx_incidents_severity
    ON observability.incidents(severity);

CREATE INDEX IF NOT EXISTS idx_incidents_detected_at
    ON observability.incidents(detected_at);