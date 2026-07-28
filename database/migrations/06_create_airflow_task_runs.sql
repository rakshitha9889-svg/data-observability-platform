CREATE TABLE IF NOT EXISTS observability.airflow_task_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    dag_id VARCHAR(250) NOT NULL,
    task_id VARCHAR(250) NOT NULL,
    dag_run_id VARCHAR(500) NOT NULL,

    event_status VARCHAR(30) NOT NULL,
    try_number INTEGER,
    logical_date TIMESTAMPTZ,
    event_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    error_type VARCHAR(250),
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_airflow_event_status
        CHECK (
            event_status IN (
                'success',
                'failed',
                'retry'
            )
        )
);


CREATE INDEX IF NOT EXISTS idx_airflow_events_dag
    ON observability.airflow_task_events(dag_id);

CREATE INDEX IF NOT EXISTS idx_airflow_events_task
    ON observability.airflow_task_events(task_id);

CREATE INDEX IF NOT EXISTS idx_airflow_events_status
    ON observability.airflow_task_events(event_status);

CREATE INDEX IF NOT EXISTS idx_airflow_events_time
    ON observability.airflow_task_events(event_time);