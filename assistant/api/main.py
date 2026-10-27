import logging
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from assistant.models import (
    IncidentAssistantResponse,
    IncidentEvidenceBundle,
    InvestigationQuestionRequest,
    InvestigationQuestionResponse,
)
from assistant.question_answerer import IncidentQuestionAnswerer
from assistant.response_generator import IncidentResponseGenerator
from assistant.retrieval.database import fetch_all
from assistant.retrieval.evidence_retriever import (
    IncidentEvidenceRetriever,
    make_json_safe,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Observability Incident Assistant",
    description=(
        "Evidence-grounded API for investigating data-quality "
        "and pipeline incidents."
    ),
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


retriever = IncidentEvidenceRetriever()
generator = IncidentResponseGenerator()

question_answerer = IncidentQuestionAnswerer()

_llm_answerer = None


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "Data Observability Incident Assistant",
        "status": "running",
        "documentation": "/docs",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }


@app.get("/api/v1/incidents")
def list_incidents(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, object]:
    conditions: list[str] = []
    parameters: dict[str, object] = {
        "result_limit": limit,
    }

    if status:
        conditions.append("LOWER(status) = LOWER(:status)")
        parameters["status"] = status

    if severity:
        conditions.append("LOWER(severity) = LOWER(:severity)")
        parameters["severity"] = severity

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    incidents = fetch_all(
        f"""
        SELECT
            incident_id,
            incident_type,
            severity,
            status,
            source,
            affected_table,
            title,
            failed_rule,
            detected_at,
            resolved_at
        FROM observability.incidents
        {where_clause}
        ORDER BY detected_at DESC
        LIMIT :result_limit;
        """,
        parameters,
    )

    return {
        "count": len(incidents),
        "incidents": make_json_safe(incidents),
    }


@app.get(
    "/api/v1/incidents/{incident_id}/evidence",
    response_model=IncidentEvidenceBundle,
)
def get_incident_evidence(
    incident_id: UUID,
) -> IncidentEvidenceBundle:
    try:
        return retriever.build_evidence_bundle(str(incident_id))
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@app.get(
    "/api/v1/incidents/{incident_id}/investigation",
    response_model=IncidentAssistantResponse,
)
def investigate_incident(
    incident_id: UUID,
) -> IncidentAssistantResponse:
    try:
        evidence_bundle = retriever.build_evidence_bundle(str(incident_id))

        return generator.generate(evidence_bundle)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


def get_llm_answerer():
    """Create the LLM answerer on first use, so the API starts without
    LLM dependencies or API keys and rule-based mode keeps working."""
    global _llm_answerer

    if _llm_answerer is None:
        from assistant.llm.llm_question_answerer import LLMQuestionAnswerer

        _llm_answerer = LLMQuestionAnswerer()

    return _llm_answerer


@app.post(
    "/api/v1/incidents/{incident_id}/questions",
    response_model=InvestigationQuestionResponse,
)
def answer_incident_question(
    incident_id: UUID,
    request: InvestigationQuestionRequest,
    mode: Literal["rules", "llm"] = Query(default="rules"),
) -> InvestigationQuestionResponse:
    try:
        evidence_bundle = retriever.build_evidence_bundle(str(incident_id))

        fallback_reason = None

        if mode == "llm":
            try:
                return get_llm_answerer().answer(
                    request.question,
                    evidence_bundle,
                )
            except Exception as error:  # noqa: BLE001 - fall back to rules
                logger.warning("LLM mode failed, using rules: %s", error)
                fallback_reason = (
                    "LLM mode was unavailable, so the rule-based "
                    f"assistant answered instead ({type(error).__name__})."
                )

        investigation = generator.generate(evidence_bundle)

        response = question_answerer.answer(
            question=request.question,
            bundle=evidence_bundle,
            investigation=investigation,
        )

        if fallback_reason:
            response.limitations.append(fallback_reason)

        return response

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error
