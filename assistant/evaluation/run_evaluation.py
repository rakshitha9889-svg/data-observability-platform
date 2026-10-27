import json
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

import requests

INCIDENT_ID = "732540bc-966d-40ef-a6c6-2dce53ad6995"

# Usage: python -m assistant.evaluation.run_evaluation [mode] [label]
#   mode:  rules (default) or llm
#   label: name for the results file, e.g. llm-claude or llm-ollama
MODE = sys.argv[1] if len(sys.argv) > 1 else "rules"
LABEL = sys.argv[2] if len(sys.argv) > 2 else MODE

API_URL = (
    f"http://localhost:8000/api/v1/incidents/{INCIDENT_ID}/questions"
    f"?mode={MODE}"
)

EVALUATION_DIRECTORY = Path(__file__).resolve().parent

QUESTIONS_FILE = EVALUATION_DIRECTORY / "questions.json"
RESULTS_FILE = EVALUATION_DIRECTORY / (
    "results.json" if LABEL == "rules" else f"results_{LABEL}.json"
)


def load_questions() -> list[dict[str, Any]]:
    with QUESTIONS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def evaluate_question(
    test_case: dict[str, Any],
) -> dict[str, Any]:
    started_at = time.perf_counter()

    response = requests.post(
        API_URL,
        json={
            "question": test_case["question"],
        },
        timeout=30,
    )

    latency_ms = (time.perf_counter() - started_at) * 1000

    response.raise_for_status()

    payload = response.json()

    answer = payload.get("answer", "")
    answer_lower = answer.lower()

    returned_type = payload.get("response_type")
    returned_refusal = payload.get("refused", False)
    citations = payload.get("citations", [])

    type_correct = returned_type == test_case["expected_type"]

    refusal_correct = returned_refusal == test_case["expected_refusal"]

    required_terms = test_case.get(
        "required_terms",
        [],
    )

    missing_terms = [
        term for term in required_terms if term.lower() not in answer_lower
    ]

    content_correct = not missing_terms

    citation_required = test_case.get(
        "citation_required",
        False,
    )

    citation_correct = bool(citations) if citation_required else True

    passed = all(
        [
            type_correct,
            refusal_correct,
            content_correct,
            citation_correct,
        ]
    )

    return {
        "question": test_case["question"],
        "expected_type": test_case["expected_type"],
        "returned_type": returned_type,
        "expected_refusal": test_case["expected_refusal"],
        "returned_refusal": returned_refusal,
        "type_correct": type_correct,
        "refusal_correct": refusal_correct,
        "content_correct": content_correct,
        "citation_correct": citation_correct,
        "missing_terms": missing_terms,
        "latency_ms": round(latency_ms, 2),
        "passed": passed,
        "answer": answer,
        "citations": citations,
    }


def calculate_percentage(
    correct: int,
    total: int,
) -> float:
    if total == 0:
        return 0.0

    return round(
        100.0 * correct / total,
        2,
    )


def main() -> None:
    questions = load_questions()

    results: list[dict[str, Any]] = []

    print(f"Running {len(questions)} evaluation questions...")

    for index, test_case in enumerate(
        questions,
        start=1,
    ):
        result = evaluate_question(test_case)
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"

        print(
            f"{index:02d}. {status} | "
            f"{result['returned_type']} | "
            f"{result['latency_ms']} ms | "
            f"{result['question']}"
        )

    total = len(results)

    passed_count = sum(result["passed"] for result in results)

    type_correct_count = sum(result["type_correct"] for result in results)

    refusal_correct_count = sum(
        result["refusal_correct"] for result in results
    )

    content_correct_count = sum(
        result["content_correct"] for result in results
    )

    citation_correct_count = sum(
        result["citation_correct"] for result in results
    )

    latencies = [result["latency_ms"] for result in results]

    summary = {
        "incident_id": INCIDENT_ID,
        "mode": MODE,
        "label": LABEL,
        "total_questions": total,
        "passed_questions": passed_count,
        "overall_pass_rate_percentage": (
            calculate_percentage(
                passed_count,
                total,
            )
        ),
        "intent_accuracy_percentage": (
            calculate_percentage(
                type_correct_count,
                total,
            )
        ),
        "refusal_accuracy_percentage": (
            calculate_percentage(
                refusal_correct_count,
                total,
            )
        ),
        "content_accuracy_percentage": (
            calculate_percentage(
                content_correct_count,
                total,
            )
        ),
        "citation_accuracy_percentage": (
            calculate_percentage(
                citation_correct_count,
                total,
            )
        ),
        "average_latency_ms": round(
            mean(latencies),
            2,
        ),
        "maximum_latency_ms": round(
            max(latencies),
            2,
        ),
    }

    output = {
        "summary": summary,
        "results": results,
    }

    with RESULTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
        )

    print()
    print("Evaluation summary")
    print(json.dumps(summary, indent=2))
    print()
    print(f"Detailed results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
