# Project Scope

## Project title

AI-Assisted Data Quality, Observability and Incident Management Platform

## Business problem

An e-commerce company receives customer, product, order, payment, shipment
and inventory data from multiple operational systems.

Missing files, duplicate records, schema changes, invalid values and delayed
data can produce incorrect KPIs and unreliable business dashboards.

The platform will ingest, validate, transform and monitor operational data.
When a quality problem occurs, it will preserve evidence, create an incident
and identify the affected tables, KPIs, dashboards and data owners.

## Users and decisions

| User | Decision supported |
|---|---|
| Data engineer | Which pipeline or dataset failed, and why? |
| Analytics engineer | Which transformation or business rule failed? |
| BI analyst | Can the affected KPI or dashboard still be trusted? |
| Operations manager | Which business process is affected? |
| Data owner | What evidence and corrective action are available? |

## In scope

- Synthetic e-commerce operational data
- Incremental CSV ingestion
- Schema and record validation
- Duplicate-file detection
- Invalid-record quarantine
- PostgreSQL raw and analytical layers
- dbt transformations and tests
- Airflow orchestration
- Pipeline-run monitoring
- Data-quality incident management
- Data lineage and impact analysis
- Streamlit engineering dashboard
- Power BI stakeholder dashboard
- Evidence-grounded incident assistant
- Automated testing and CI/CD

## Out of scope

- Real customer personal data
- Real payment-card information
- Production payment processing
- Automated correction of source data
- Autonomous execution of incident fixes
- Production-scale cloud infrastructure during the initial MVP

## Business KPIs

1. Daily order volume
2. Gross revenue
3. Average order value
4. Payment success rate
5. Cancellation rate
6. On-time delivery rate
7. Average delivery delay
8. Stockout rate
9. Number of low-inventory products

## Quality dimensions

| Dimension | Example expectation |
|---|---|
| Completeness | Primary identifiers must not be null |
| Uniqueness | Primary identifiers must be unique |
| Validity | Amounts and quantities must be non-negative |
| Integrity | Every order customer must exist |
| Consistency | Order totals should match order-item totals |
| Freshness | The latest expected batch must be available |
| Volume | Daily volume must remain within an expected range |

## Initial success criteria

- Generate at least 90 days of operational data
- Support at least seven source entities
- Load files incrementally and transactionally
- Prevent duplicate file ingestion
- Quarantine invalid records with failure evidence
- Implement at least 25 automated data-quality tests
- Reproduce at least 10 data incidents
- Trace failures to affected downstream assets
- Provide measurable detection and investigation results