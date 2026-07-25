CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS observability;
CREATE SCHEMA IF NOT EXISTS quarantine;

COMMENT ON SCHEMA raw IS
    'Append-only records received from source systems.';

COMMENT ON SCHEMA staging IS
    'Cleaned, typed and standardized source records.';

COMMENT ON SCHEMA analytics IS
    'Business-ready dimensional models and analytical marts.';

COMMENT ON SCHEMA observability IS
    'Pipeline runs, files, tests, incidents and lineage metadata.';

COMMENT ON SCHEMA quarantine IS
    'Invalid records preserved with data-quality failure evidence.';