CREATE TABLE IF NOT EXISTS observability.failure_experiments (
    experiment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    scenario_name VARCHAR(150) NOT NULL,
    batch_date DATE NOT NULL,
    expected_detection_layer VARCHAR(100) NOT NULL,
    expected_severity VARCHAR(20) NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'prepared',
    detected BOOLEAN NOT NULL DEFAULT FALSE,
    actual_detection_layer VARCHAR(100),

    prepared_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    detected_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    time_to_detection_seconds NUMERIC(12, 3),
    notes TEXT,

    CONSTRAINT chk_experiment_status
        CHECK (
            status IN (
                'prepared',
                'running',
                'detected',
                'not_detected',
                'completed'
            )
        ),

    CONSTRAINT chk_experiment_severity
        CHECK (
            expected_severity IN (
                'critical',
                'high',
                'medium',
                'low'
            )
        )
);


ALTER TABLE observability.incidents
ADD COLUMN IF NOT EXISTS experiment_id UUID;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_incident_experiment'
    ) THEN
        ALTER TABLE observability.incidents
        ADD CONSTRAINT fk_incident_experiment
            FOREIGN KEY (experiment_id)
            REFERENCES observability.failure_experiments(
                experiment_id
            );
    END IF;
END
$$;


CREATE INDEX IF NOT EXISTS idx_failure_experiment_scenario
    ON observability.failure_experiments(scenario_name);

CREATE INDEX IF NOT EXISTS idx_failure_experiment_status
    ON observability.failure_experiments(status);

CREATE INDEX IF NOT EXISTS idx_failure_experiment_batch
    ON observability.failure_experiments(batch_date);

CREATE INDEX IF NOT EXISTS idx_incident_experiment
    ON observability.incidents(experiment_id);