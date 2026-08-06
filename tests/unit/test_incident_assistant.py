from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from assistant.models import (
    EvidenceRecord,
    IncidentEvidenceBundle,
)
from assistant.question_answerer import IncidentQuestionAnswerer
from assistant.response_generator import IncidentResponseGenerator
from assistant.retrieval.evidence_retriever import make_json_safe

INCIDENT_ID = "732540bc-966d-40ef-a6c6-2dce53ad6995"


@pytest.fixture
def incident_evidence() -> EvidenceRecord:
    return EvidenceRecord(
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
            "description": (
                "1 invalid record was quarantined before reaching raw tables."
            ),
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
                        "entity_name": "payments",
                        "source_file": ("payments_2026-04-09.csv"),
                        "source_row_number": 2,
                        "failed_rule": ("amount must not be negative"),
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


@pytest.fixture
def evidence_bundle(
    incident_evidence: EvidenceRecord,
) -> IncidentEvidenceBundle:
    return IncidentEvidenceBundle(
        incident_id=INCIDENT_ID,
        incident=incident_evidence,
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
def investigation(evidence_bundle):
    generator = IncidentResponseGenerator()

    return generator.generate(evidence_bundle)


def test_make_json_safe_converts_supported_types():
    value = {
        "uuid": UUID(INCIDENT_ID),
        "timestamp": datetime(
            2026,
            7,
            29,
            15,
            18,
            tzinfo=timezone.utc,
        ),
        "decimal": Decimal("10.50"),
        "nested": [
            Decimal("2.25"),
        ],
    }

    result = make_json_safe(value)

    assert result["uuid"] == INCIDENT_ID

    assert result["timestamp"] == ("2026-07-29T15:18:00+00:00")

    assert result["decimal"] == 10.5
    assert result["nested"] == [2.25]


def test_response_generator_creates_grounded_summary(
    evidence_bundle,
):
    generator = IncidentResponseGenerator()

    response = generator.generate(evidence_bundle)

    assert response.incident_id == INCIDENT_ID
    assert response.confidence == "medium"
    assert "negative_payment" in response.incident_summary
    assert "data_quality" in response.incident_summary
    assert "critical" in response.incident_summary
    assert "resolved" in response.incident_summary

    assert evidence_bundle.incident.evidence_id in response.citations


def test_response_contains_quarantine_evidence(
    evidence_bundle,
):
    generator = IncidentResponseGenerator()

    response = generator.generate(evidence_bundle)

    combined_evidence = " ".join(response.confirmed_evidence)

    assert "PAY_00000631" in combined_evidence
    assert "-500.0" in combined_evidence

    assert "payments_2026-04-09.csv" in combined_evidence

    assert "amount must not be negative" in combined_evidence


def test_response_does_not_invent_affected_assets(
    evidence_bundle,
):
    generator = IncidentResponseGenerator()

    response = generator.generate(evidence_bundle)

    combined_assets = " ".join(response.affected_assets)

    assert "impact is unknown" in combined_assets.lower()

    assert "not necessarily absent" in combined_assets.lower()


def test_response_does_not_claim_remediation_execution(
    evidence_bundle,
):
    generator = IncidentResponseGenerator()

    response = generator.generate(evidence_bundle)

    combined_recommendations = " ".join(response.recommended_investigation)

    assert "verify" in combined_recommendations.lower()

    assert "executed remediation" not in (combined_recommendations.lower())


@pytest.mark.parametrize(
    (
        "question",
        "expected_response_type",
    ),
    [
        (
            "What happened in this incident?",
            "incident_summary",
        ),
        (
            "Describe this incident.",
            "incident_summary",
        ),
        (
            "What was the root cause?",
            "cause_or_hypothesis",
        ),
        (
            "What evidence confirms the invalid payment?",
            "confirmed_evidence",
        ),
        (
            "Which downstream KPIs were affected?",
            "affected_assets",
        ),
        (
            "What is the status and severity?",
            "status",
        ),
        (
            "Were any dbt tests related?",
            "quality_tests",
        ),
        (
            "Are there relevant Airflow logs?",
            "airflow_logs",
        ),
        (
            "What should the engineer investigate next?",
            "recommended_investigation",
        ),
    ],
)
def test_supported_question_routing(
    evidence_bundle,
    investigation,
    question,
    expected_response_type,
):
    answerer = IncidentQuestionAnswerer()

    response = answerer.answer(
        question=question,
        bundle=evidence_bundle,
        investigation=investigation,
    )

    assert response.response_type == (expected_response_type)

    assert response.refused is False
    assert response.answer


@pytest.mark.parametrize(
    "question",
    [
        "What will the weather be tomorrow?",
        "Who won the football match?",
        "Write a recipe for pasta.",
    ],
)
def test_unsupported_questions_are_refused(
    evidence_bundle,
    investigation,
    question,
):
    answerer = IncidentQuestionAnswerer()

    response = answerer.answer(
        question=question,
        bundle=evidence_bundle,
        investigation=investigation,
    )

    assert response.response_type == "unsupported"
    assert response.refused is True
    assert response.confidence == "low"
    assert response.citations == []

    assert "cannot answer" in response.answer.lower()


def test_quality_test_question_reports_missing_evidence(
    evidence_bundle,
    investigation,
):
    answerer = IncidentQuestionAnswerer()

    response = answerer.answer(
        question=("Were any dbt tests related to this incident?"),
        bundle=evidence_bundle,
        investigation=investigation,
    )

    assert response.response_type == "quality_tests"

    assert "no directly related failed dbt" in response.answer.lower()


def test_airflow_question_does_not_attach_unrelated_logs(
    evidence_bundle,
    investigation,
):
    answerer = IncidentQuestionAnswerer()

    response = answerer.answer(
        question="Are there relevant Airflow logs?",
        bundle=evidence_bundle,
        investigation=investigation,
    )

    assert response.response_type == "airflow_logs"

    assert "will not attach unrelated" in response.answer.lower()
