DO $$
DECLARE
    schema_count INTEGER;
    required_table_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO schema_count
    FROM information_schema.schemata
    WHERE schema_name IN (
        'raw',
        'staging',
        'analytics',
        'observability',
        'quarantine'
    );

    IF schema_count <> 5 THEN
        RAISE EXCEPTION
            'Expected 5 project schemas, found %',
            schema_count;
    END IF;

    SELECT COUNT(*)
    INTO required_table_count
    FROM information_schema.tables
    WHERE table_schema || '.' || table_name IN (
        'raw.customers',
        'raw.products',
        'raw.orders',
        'raw.order_items',
        'raw.payments',
        'raw.shipments',
        'raw.inventory',
        'observability.pipeline_runs',
        'observability.ingested_files',
        'observability.quality_test_results',
        'observability.incidents',
        'quarantine.invalid_records'
    );

    IF required_table_count <> 12 THEN
        RAISE EXCEPTION
            'Expected 12 initial tables, found %',
            required_table_count;
    END IF;

    RAISE NOTICE
        'Database verification succeeded: % schemas and % tables found.',
        schema_count,
        required_table_count;
END
$$;