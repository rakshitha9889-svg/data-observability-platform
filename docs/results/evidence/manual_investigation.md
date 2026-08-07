# Manual Incident Investigation

- Incident ID: 1d2cb9de-abdb-4e46-8ab5-805b0d035109
- Title: Ingestion validation failure: null_customer_id
- Incident type: data_quality
- Severity: medium
- Status: reolved
- Source: ingestion_validation
- Affected entity: orders
- Affected table: raw.orders
- Failed rule: customer_id must not be null or empty
- Supporting evidence: - Supporting evidence: Row 2 from orders_2026-04-07.csv was
  quarantined because customer_id must not be null or empty. The quarantined record shows
  {"status": "completed", "currency": "EUR", "order_id": "ORD_00000478", "order_date": "2026-04-07 18:23:01", "customer_id": null, "order_total": 395.12}.
- Detection time: 2026-07-29 15:46:09.328542+00
- Resolution status: Experimental source rows removed and the clean analytical baseline restored.
- Likely cause:  The recorded failure experiment indicates eAn order has a null customer ID. Experiment evidence preserved and experimental source rows cleaned.The severity of incident is medium .
- Recommended next action: Correct or replace the invalid source record,
  validate the required customer identifier against the customer source,
  rerun ingestion idempotently and confirm that the record is no longer
  quarantined.
- Evidence limitations: No downstream impacted assets were recorded for this
  incident.
