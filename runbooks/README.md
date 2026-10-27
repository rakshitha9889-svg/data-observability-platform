# Incident runbooks

One file per failure scenario in `configs/failure_scenarios.yaml`, named
after the scenario key. The LLM triage mode retrieves these sections as
evidence, so keep every file on the same six `##` headings:

Symptoms · Where it is detected · Likely causes · How to confirm · Fix ·
Prevention

`negative_payment.md` is complete. The other files start with the facts
from the scenario config; replace every `TODO` line with your own words.
Sections that still start with `TODO` are skipped by the indexer.

After editing, re-index:

```bash
python -m assistant.rag.index_runbooks
```
