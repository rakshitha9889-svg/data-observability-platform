import pytest
from fastapi.testclient import TestClient

from assistant.api.main import app
from assistant.models import (
    EvidenceRecord,
    IncidentEvidenceBundle,
)

INCIDENT_ID = "732540bc-966d-40ef-a6c6-2dce53ad6995"

MISSING_INCIDENT_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def evidence_bundle() -> IncidentEvidenceBundle:
    incident = EvidenceRecord(
        evidence_id=(f"observability.incidents:{INCIDENT_ID}"),
        source_table="observability.incidents",
        record={
            "incident_id": INCIDENT_ID,
            "incident_type": "data_quality",
            "severity": "critical",
            "status": "resolved",
            "source": "ingestion_validation",
            "affected_entity": "payments",
            "affected_table": "raw.payments",
            "title": ("Ingestion validation failure: negative_payment"),
            "description": ("One invalid payment record was quarantined."),
            "failed_rule": "amount must not be negative",
            "suspected_cause": None,
            "detected_at": "2026-07-29T15:18:35+00:00",
            "resolved_at": "2026-07-29T15:33:20+00:00",
            "resolution_notes": (
                "The clean analytical baseline was restored."
            ),
            "evidence": {
                "quarantined_record_count": 1,
                "injection_evidence": {
                    "change": ("Set the first payment amount to -500.00."),
                    "affected_file": ("payments_2026-04-09.csv"),
                    "affected_value": "PAY_00000631",
                },
                "records": [
                    {
                        "source_file": ("payments_2026-04-09.csv"),
                        "source_row_number": 2,
                        "failure_reason": ("amount must not be negative"),
                        "record_data": {
                            "payment_id": "PAY_00000631",
                            "amount": -500.0,
                        },
                    }
                ],
            },
        },
    )

    return IncidentEvidenceBundle(
        incident_id=INCIDENT_ID,
        incident=incident,
        failed_tests=[],
        relevant_logs=[],
        similar_incidents=[],
        affected_assets=[],
        limitations=[
            ("No directly related failed quality-test records were found."),
            ("No relevant Airflow error logs were found."),
            ("No downstream impacted assets were recorded."),
        ],
    )


@pytest.fixture
def client(
    monkeypatch,
    evidence_bundle,
) -> TestClient:
    def fake_build_evidence_bundle(
        incident_id: str,
    ) -> IncidentEvidenceBundle:
        if incident_id == MISSING_INCIDENT_ID:
            raise ValueError(f"Incident does not exist: {incident_id}")

        return evidence_bundle

    monkeypatch.setattr(
        ("assistant.api.main.retriever.build_evidence_bundle"),
        fake_build_evidence_bundle,
    )

    return TestClient(app)


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "running"

    assert payload["documentation"] == "/docs"


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
    }


def test_evidence_endpoint_returns_bundle(client):
    response = client.get(f"/api/v1/incidents/{INCIDENT_ID}/evidence")

    assert response.status_code == 200

    payload = response.json()

    assert payload["incident_id"] == INCIDENT_ID

    assert payload["incident"]["record"]["failed_rule"] == (
        "amount must not be negative"
    )

    assert payload["failed_tests"] == []
    assert payload["relevant_logs"] == []


def test_investigation_endpoint_is_grounded(client):
    response = client.get((f"/api/v1/incidents/{INCIDENT_ID}/investigation"))

    assert response.status_code == 200

    payload = response.json()

    assert payload["incident_id"] == INCIDENT_ID
    assert payload["confidence"] == "medium"

    assert "negative_payment" in (payload["incident_summary"])

    assert payload["citations"] == [(f"observability.incidents:{INCIDENT_ID}")]


@pytest.mark.parametrize(
    (
        "question",
        "expected_type",
        "expected_refusal",
    ),
    [
        (
            "What happened in this incident?",
            "incident_summary",
            False,
        ),
        (
            "What evidence confirms the payment?",
            "confirmed_evidence",
            False,
        ),
        (
            "Which downstream assets were affected?",
            "affected_assets",
            False,
        ),
        (
            "What will the weather be tomorrow?",
            "unsupported",
            True,
        ),
    ],
)
def test_question_endpoint(
    client,
    question,
    expected_type,
    expected_refusal,
):
    response = client.post(
        (f"/api/v1/incidents/{INCIDENT_ID}/questions"),
        json={
            "question": question,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["response_type"] == expected_type
    assert payload["refused"] is expected_refusal
    assert payload["answer"]


def test_question_validation_rejects_empty_question(client):
    response = client.post(
        (f"/api/v1/incidents/{INCIDENT_ID}/questions"),
        json={
            "question": "",
        },
    )

    assert response.status_code == 422


def test_question_validation_rejects_missing_body(client):
    response = client.post((f"/api/v1/incidents/{INCIDENT_ID}/questions"))

    assert response.status_code == 422


def test_missing_incident_returns_404(client):
    response = client.get(
        (f"/api/v1/incidents/{MISSING_INCIDENT_ID}/investigation")
    )

    assert response.status_code == 404

    assert "does not exist" in (response.json()["detail"])


def test_invalid_uuid_returns_422(client):
    response = client.get("/api/v1/incidents/not-a-uuid/investigation")

    assert response.status_code == 422


class FakeLLMAnswerer:
    def answer(self, question, bundle):
        from assistant.models import InvestigationQuestionResponse

        return InvestigationQuestionResponse(
            incident_id=bundle.incident_id,
            question=question,
            answer="Hypothesis: a negative payment amount.",
            response_type="cause_or_hypothesis",
            confidence="medium",
            citations=[bundle.incident.evidence_id],
        )


def test_llm_mode_uses_llm_answerer(client, monkeypatch):
    monkeypatch.setattr(
        "assistant.api.main.get_llm_answerer",
        lambda: FakeLLMAnswerer(),
    )

    response = client.post(
        f"/api/v1/incidents/{INCIDENT_ID}/questions?mode=llm",
        json={"question": "What was the likely root cause?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Hypothesis: a negative payment amount."
    assert payload["citations"] == [f"observability.incidents:{INCIDENT_ID}"]


def test_llm_mode_falls_back_to_rules(client, monkeypatch):
    def unavailable():
        raise RuntimeError("no API key")

    monkeypatch.setattr("assistant.api.main.get_llm_answerer", unavailable)

    response = client.post(
        f"/api/v1/incidents/{INCIDENT_ID}/questions?mode=llm",
        json={"question": "What was the likely root cause?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response_type"] == "cause_or_hypothesis"
    assert any("rule-based" in note for note in payload["limitations"])


def test_unknown_mode_returns_422(client):
    response = client.post(
        f"/api/v1/incidents/{INCIDENT_ID}/questions?mode=magic",
        json={"question": "What happened?"},
    )

    assert response.status_code == 422
