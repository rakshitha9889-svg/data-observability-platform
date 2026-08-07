# Final Results and Experiment Tracker

## Reproducibility information

- Experiment date: 2026-08-06T18:15:03Z
- Git commit: `7189f63a4164df758c8057c7633d911db8e83b42`
- Execution environment: macOS, Python 3.13.5, PostgreSQL 16, Docker Compose
- Evidence directory: `docs/results/evidence/`

## Final measured results

| Metric | Final value | Evidence |
|---|---:|---|
| Source entity feeds | 7 | `database_metrics.txt` |
| Deduplicated records processed | 21,432 | `database_metrics.txt` |
| Raw tables | 7 | `database_metrics.txt` |
| Analytical tables | 7 | `database_metrics.txt` |
| Raw and analytical tables | 14 | `database_metrics.txt` |
| Observability tables | 9 | `database_metrics.txt` |
| Quarantine tables | 1 | `database_metrics.txt` |
| dbt models | 18 | `dbt_resource_counts.txt` |
| Automated dbt tests | 60 | `dbt_resource_counts.txt` |
| Python tests passed | 38 | `pytest_coverage.txt` |
| Failure scenarios executed | 11 | `database_metrics.txt` |
| Injected failures detected | 11 of 11 |
| Failure-detection rate | 100.00% | `database_metrics.txt` |
| Lineage assets mapped | 96 | `database_metrics.txt` |
| Lineage relationships mapped | 102 | `database_metrics.txt` |
| Average pipeline runtime | 0.14 seconds | `database_metrics.txt` |
| Assistant-package test coverage | 77.90% | `assistant_coverage.json` |
| Full-codebase coverage baseline | 23.36% | `coverage_baseline.json` |
| Assistant evaluation questions | 25 | `assistant_evaluation.json` |
| Assistant evaluation pass rate | 100.00% | `assistant_evaluation.json` |
| Assistant intent accuracy | 100.00% | `assistant_evaluation.json` |
| Assistant content accuracy | 100.00% | `assistant_evaluation.json` |
| Assistant citation accuracy | 100.00% | `assistant_evaluation.json` |
| Assistant refusal accuracy | 100.00% | `assistant_evaluation.json` |
| Unsupported-claim rate | 0.00% | `unsupported_claim_rate.txt` |
| Average assistant latency | 7.58 ms | `assistant_evaluation.json` |
| Maximum assistant latency | 69.57 ms | `assistant_evaluation.json` |
| Manual investigation time | 14.88 minutes | `investigation_comparison.json` |
| Assisted investigation time | 9.73 minutes | `investigation_comparison.json` |
| Investigation time saved | 5.15 minutes | `investigation_comparison.json` |
| Investigation time reduction | 34.60% | `investigation_comparison.json` |

## Investigation-time experiment

The manual investigation used incident
`1d2cb9de-abdb-4e46-8ab5-805b0d035109`, a medium-severity
ingestion-validation incident affecting `raw.orders`.

The assistant-assisted investigation used incident
`883bcb2b-64b0-4fb2-b25f-f9389e1ec7b2`, another medium-severity
ingestion-validation incident affecting `raw.orders`.

The manual investigation required 893 seconds, while the
assistant-assisted investigation required 584 seconds. This saved
309 seconds, or 5.15 minutes, representing a 34.60% reduction in
investigation time.

Both investigations required identifying the incident summary,
affected table, failed rule, supporting evidence, detection and
resolution status, likely cause, recommended action and evidence
limitations.

## Metric definitions

### Source entity feeds

The platform processed seven distinct source entities. These are described as
source feeds rather than seven different file formats because the current
implementation uses CSV input files.

### Records processed

The records-processed metric is calculated from unique file checksums to prevent
idempotent reruns from inflating the result.

### Raw and analytical tables

This metric includes seven tables in the `raw` schema and seven tables in the
`analytics` schema. Observability and quarantine tables are reported separately.

### Failure-detection rate

The platform detected all 11 recorded failure experiments:

`11 detected / 11 executed * 100 = 100.00%`

### Test coverage

All 38 Python tests passed with no skipped tests. The configured CI coverage
scope is the `assistant` package, which achieved 77.90% branch-aware coverage
and exceeded the required 60% threshold.

A broader baseline measurement covering `assistant`, `ingestion` and
`observability` produced 23.36% coverage. This broader value is retained
separately and shows that ingestion, incident-management, quality and lineage
modules require additional tests before making a project-wide coverage claim.

### Assistant evaluation

The evidence-grounded incident assistant passed all 25 evaluation questions.
It achieved 100% intent, refusal, content and citation accuracy on the recorded
evaluation dataset. The measured unsupported-claim rate was 0%.

## Accuracy limitations

- The evaluation dataset contains only 25 assistant questions.
- The failure-detection result covers the 11 implemented experiments and should
  not be generalized to every possible production failure.
- Pipeline runtime was measured locally using a relatively small synthetic
  dataset.
- Seven source entities were processed, but the current source-file format is
  CSV.
- Investigation time was measured using one comparable incident pair. The 34.60% reduction is a controlled demonstration and should not be generalized without repeated trials.
- The 77.90% coverage result applies to the configured `assistant` package scope. The broader full-codebase baseline is 23.36%.

## Reproduction commands

Database metrics:

```bash
cat docs/results/evidence/database_metrics.txt

Investigation-time comparison:

```bash
cat docs/results/evidence/investigation_times.csv
cat docs/results/evidence/investigation_comparison.json


```bash
cat docs/results/evidence/assistant_coverage_summary.txt
cat docs/results/evidence/assistant_coverage.txt

