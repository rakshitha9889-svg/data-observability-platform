# Incident Assistant Evaluation

The evidence-grounded incident assistant was evaluated using 25 known
investigation questions covering:

- Incident identification and summarization
- Confirmed evidence retrieval
- Root-cause hypotheses
- Downstream impact
- dbt quality-test evidence
- Airflow task evidence
- Recommended investigation
- Unsupported-question refusal

## Metrics

The automated evaluation reports:

- Overall pass rate
- Intent classification accuracy
- Refusal accuracy
- Content accuracy
- Citation accuracy
- Average response latency
- Maximum response latency

Detailed machine-readable results are available in `results.json`.

## Safety behavior

The assistant:

- Uses only permitted operational evidence
- Includes evidence identifiers with supported factual claims
- Separates confirmed facts from hypotheses
- Reports missing evidence as a limitation
- Does not claim that remediation was executed
- Refuses unsupported questions