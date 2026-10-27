"""Ask every injected-failure incident for its root cause and check that the
answer names the real scenario.

Usage (API running on port 8000):

    python -m assistant.evaluation.root_cause_eval rules
    python -m assistant.evaluation.root_cause_eval llm llm-claude
    python -m assistant.evaluation.root_cause_eval llm llm-ollama

REQUIRED_WORDS was written before any run. Do not edit it to make a
failing answer pass; change it only if a scenario's meaning changes.
"""

import json
import sys
import time
from pathlib import Path
from statistics import mean

import requests
from sqlalchemy import text

from assistant.config import get_database_engine

MODE = sys.argv[1] if len(sys.argv) > 1 else "rules"
LABEL = sys.argv[2] if len(sys.argv) > 2 else MODE

API_BASE = "http://localhost:8000/api/v1/incidents"
QUESTION = "What was the likely root cause of this incident?"
RESULTS_FILE = Path(__file__).resolve().parent / f"root_cause_{LABEL}.json"

# Every word must appear in the answer (case-insensitive).
REQUIRED_WORDS: dict[str, list[str]] = {
    "missing_payments_file": ["payment", "file", "missing"],
    "duplicate_order_id": ["duplicate", "order"],
    "null_customer_id": ["null", "customer"],
    "unknown_customer_id": ["customer", "exist"],
    "negative_payment": ["negative", "payment"],
    "removed_order_column": ["customer_id", "column"],
    "order_volume_drop": ["order", "volume"],
    "excessive_delivery_delay": ["delivery", "delay"],
    "invalid_order_status": ["order", "status"],
    "order_total_mismatch": ["total", "mismatch"],
}

INCIDENTS_BY_SCENARIO = text(
    "SELECT DISTINCT ON (experiment.scenario_name) "
    "incident.incident_id, experiment.scenario_name "
    "FROM observability.incidents AS incident "
    "JOIN observability.failure_experiments AS experiment "
    "ON experiment.experiment_id = incident.experiment_id "
    "ORDER BY experiment.scenario_name, incident.incident_id"
)


def is_correct(scenario: str, answer: str) -> bool:
    words = REQUIRED_WORDS.get(scenario, [])
    answer_lower = answer.lower()
    return bool(words) and all(word in answer_lower for word in words)


def main() -> None:
    with get_database_engine().connect() as connection:
        incidents = connection.execute(INCIDENTS_BY_SCENARIO).mappings().all()

    if not incidents:
        raise SystemExit("No incidents linked to failure experiments found.")

    results = []

    for row in incidents:
        url = f"{API_BASE}/{row['incident_id']}/questions?mode={MODE}"
        started = time.perf_counter()
        response = requests.post(url, json={"question": QUESTION}, timeout=90)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        response.raise_for_status()
        payload = response.json()

        correct = is_correct(row["scenario_name"], payload["answer"])
        results.append(
            {
                "scenario": row["scenario_name"],
                "incident_id": str(row["incident_id"]),
                "correct": correct,
                "latency_ms": latency_ms,
                "citations": payload.get("citations", []),
                "limitations": payload.get("limitations", []),
                "answer": payload["answer"],
            }
        )
        status = "PASS" if correct else "FAIL"
        print(f"{status} | {row['scenario_name']} | {latency_ms} ms")

    passed = sum(result["correct"] for result in results)
    removed = sum(
        "citation(s) removed" in note
        for result in results
        for note in result["limitations"]
    )
    summary = {
        "mode": MODE,
        "label": LABEL,
        "root_causes_correct": passed,
        "incidents": len(results),
        "answers_with_removed_citations": removed,
        "average_latency_ms": round(mean(r["latency_ms"] for r in results), 1),
    }

    RESULTS_FILE.write_text(
        json.dumps({"summary": summary, "results": results}, indent=2),
        encoding="utf-8",
    )
    print(f"{LABEL}: {passed} of {len(results)} root causes correct")
    print(f"Saved {RESULTS_FILE.name}")


if __name__ == "__main__":
    main()
