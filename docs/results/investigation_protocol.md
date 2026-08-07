# Incident Investigation-Time Experiment

## Objective

Compare the time required to investigate an incident manually against the time
required using the evidence-grounded incident assistant.

## Experiment design

Two resolved incidents with comparable severity and complexity will be selected.

- Incident A will be investigated manually using PostgreSQL queries.
- Incident B will be investigated using the incident-assistant API.
- The timer starts immediately before the first investigation command.
- The timer stops after documenting the incident type, affected table, failed
  rule, evidence, likely cause and resolution.
- Application startup time is excluded.
- Results are recorded in seconds and converted to minutes.
- The incidents and commands used are retained as reproducibility evidence.

## Required investigation output

An investigation is complete only when it identifies:

1. Incident title and type
2. Severity and status
3. Affected entity or table
4. Failed validation or quality rule
5. Supporting evidence
6. Detection time
7. Resolution status or recommended next action

## Limitations

The comparison uses different incidents to reduce learning carryover. Incident
difficulty may still vary, so the result is presented as a small controlled
demonstration rather than a general productivity benchmark.