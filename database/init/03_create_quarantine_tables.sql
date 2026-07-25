CREATE TABLE IF NOT EXISTS quarantine.invalid_records (
    quarantine_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    run_id UUID NOT NULL,
    file_id UUID,

    entity_name VARCHAR(100) NOT NULL,
    source_file VARCHAR(500) NOT NULL,
    source_row_number BIGINT,

    failed_rule VARCHAR(500) NOT NULL,
    failure_type VARCHAR(100) NOT NULL,
    failure_reason TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',

    record_data JSONB NOT NULL,

    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,

    CONSTRAINT fk_quarantine_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT fk_quarantine_file
        FOREIGN KEY (file_id)
        REFERENCES observability.ingested_files(file_id),

    CONSTRAINT chk_quarantine_severity
        CHECK (
            severity IN (
                'critical',
                'high',
                'medium',
                'low'
            )
        ),

    CONSTRAINT chk_quarantine_row_number
        CHECK (
            source_row_number IS NULL
            OR source_row_number > 0
        ),

    CONSTRAINT chk_quarantine_resolution
        CHECK (
            resolved_at IS NULL
            OR resolved = TRUE
        )
);


CREATE INDEX IF NOT EXISTS idx_quarantine_run_id
    ON quarantine.invalid_records(run_id);

CREATE INDEX IF NOT EXISTS idx_quarantine_file_id
    ON quarantine.invalid_records(file_id);

CREATE INDEX IF NOT EXISTS idx_quarantine_entity
    ON quarantine.invalid_records(entity_name);

CREATE INDEX IF NOT EXISTS idx_quarantine_failed_rule
    ON quarantine.invalid_records(failed_rule);

CREATE INDEX IF NOT EXISTS idx_quarantine_time
    ON quarantine.invalid_records(quarantined_at);

CREATE INDEX IF NOT EXISTS idx_quarantine_unresolved
    ON quarantine.invalid_records(resolved)
    WHERE resolved = FALSE;