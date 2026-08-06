import pytest
from sqlalchemy.exc import SQLAlchemyError

from assistant.question_answerer import IncidentQuestionAnswerer
from assistant.response_generator import IncidentResponseGenerator
from assistant.retrieval.database import fetch_one
from assistant.retrieval.evidence_retriever import (
    IncidentEvidenceRetriever,
)

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def stored_incident():
    try:
        incident = fetch_one(
            """
            SELECT
                incident_id,
                title,
                status,
                severity
            FROM observability.incidents
            WHERE title ILIKE '%negative_payment%'
            ORDER BY detected_at DESC
            LIMIT 1;
            """
        )

    except (SQLAlchemyError, RuntimeError) as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")

    if incident is None:
        pytest.skip("No negative_payment incident is available.")

    return incident


@pytest.fixture(scope="module")
def evidence_bundle(stored_incident):
    retriever = IncidentEvidenceRetriever()

    return retriever.build_evidence_bundle(str(stored_incident["incident_id"]))


@pytest.fixture(scope="module")
def investigation(evidence_bundle):
    generator = IncidentResponseGenerator()

    return generator.generate(evidence_bundle)


def test_database_incident_is_retrieved(
    stored_incident,
):
    assert "negative_payment" in (stored_incident["title"])

    assert stored_incident["severity"] == "critical"

    assert stored_incident["status"] in {
        "open",
        "resolved",
    }


def test_complete_evidence_bundle_is_created(
    evidence_bundle,
):
    incident = evidence_bundle.incident.record

    assert incident["incident_type"] == "data_quality"
    assert incident["affected_table"] == "raw.payments"

    assert incident["failed_rule"] == ("amount must not be negative")

    assert incident["evidence"]


def test_grounded_investigation_is_generated(
    investigation,
    evidence_bundle,
):
    assert investigation.incident_id == (evidence_bundle.incident_id)

    assert investigation.confidence in {
        "medium",
        "high",
    }

    assert "negative_payment" in (investigation.incident_summary)

    assert evidence_bundle.incident.evidence_id in investigation.citations


def test_quarantined_payment_evidence_is_present(
    investigation,
):
    combined_evidence = " ".join(investigation.confirmed_evidence)

    assert "PAY_00000631" in combined_evidence
    assert "-500.0" in combined_evidence

    assert "payments_2026-04-09.csv" in combined_evidence


def test_supported_question_is_answered(
    evidence_bundle,
    investigation,
):
    answerer = IncidentQuestionAnswerer()

    response = answerer.answer(
        question=("What evidence confirms the invalid payment?"),
        bundle=evidence_bundle,
        investigation=investigation,
    )

    assert response.refused is False

    assert response.response_type == ("confirmed_evidence")

    assert response.citations


def test_unsupported_question_is_refused(
    evidence_bundle,
    investigation,
):
    answerer = IncidentQuestionAnswerer()

    response = answerer.answer(
        question="What will the weather be tomorrow?",
        bundle=evidence_bundle,
        investigation=investigation,
    )

    assert response.refused is True
    assert response.response_type == "unsupported"
    assert response.confidence == "low"
    assert response.citations == []


def test_missing_lineage_is_reported_as_unknown(
    evidence_bundle,
    investigation,
):
    if evidence_bundle.affected_assets:
        pytest.skip("The selected incident now has lineage evidence.")

    combined_assets = " ".join(investigation.affected_assets).lower()

    assert "unknown" in combined_assets

    assert "not necessarily absent" in (combined_assets)
