# Failure Experiment Results

## Summary

- Total scenarios: 10
- Detected scenarios: 10
- Detection rate: 100.0%
- Average time to detection: 3.178 seconds
- Correct detection-layer rate: 100.0%

## Scenario results

| scenario_name | batch_date | expected_detection_layer | actual_detection_layer | expected_severity | detected | time_to_detection_seconds | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| duplicate_order_id | 2026-04-06 | ingestion_validation | ingestion_validation | medium | True | 1.299 | completed |
| excessive_delivery_delay | 2026-04-12 | dbt_business_rule | dbt_business_rule | medium | True | 8.379 | completed |
| invalid_order_status | 2026-04-13 | ingestion_validation | ingestion_validation | medium | True | 1.516 | completed |
| missing_payments_file | 2026-04-05 | pre_ingestion | pre_ingestion | high | True | 0.011 | completed |
| negative_payment | 2026-04-09 | ingestion_validation | ingestion_validation | critical | True | 1.472 | completed |
| null_customer_id | 2026-04-07 | ingestion_validation | ingestion_validation | medium | True | 1.478 | completed |
| order_total_mismatch | 2026-04-14 | dbt_reconciliation_test | dbt_reconciliation_test | critical | True | 7.937 | completed |
| order_volume_drop | 2026-04-11 | pre_ingestion | pre_ingestion | high | True | 0.014 | completed |
| removed_order_column | 2026-04-10 | schema_validation | schema_validation | high | True | 1.56 | completed |
| unknown_customer_id | 2026-04-08 | dbt_relationship_test | dbt_relationship_test | high | True | 8.119 | completed |
