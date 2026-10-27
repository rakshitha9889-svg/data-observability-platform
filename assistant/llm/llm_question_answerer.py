from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from assistant.models import (
    EvidenceRecord,
    IncidentEvidenceBundle,
    InvestigationQuestionResponse,
)
from assistant.prompts.llm_triage import SYSTEM_PROMPT, build_user_message

ResponseType = Literal[
    "incident_summary",
    "cause_or_hypothesis",
    "confirmed_evidence",
    "affected_assets",
    "quality_tests",
    "airflow_logs",
    "recommended_investigation",
    "status",
    "unsupported",
]


class LLMAnswer(BaseModel):
    response_type: ResponseType
    answer: str
    citations: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    refused: bool = False


def default_runbook_search(query: str) -> list[EvidenceRecord]:
    from assistant.rag.runbook_retriever import search_runbooks

    return search_runbooks(query)


def build_runbook_query(
    question: str,
    bundle: IncidentEvidenceBundle,
) -> str:
    incident = bundle.incident.record
    context = [
        str(incident.get(key, ""))
        for key in ("incident_type", "source", "affected_table", "title")
    ]
    return " ".join([question, *[value for value in context if value]])


def all_evidence(
    bundle: IncidentEvidenceBundle,
    runbooks: list[EvidenceRecord],
) -> list[EvidenceRecord]:
    return [
        bundle.incident,
        *bundle.failed_tests,
        *bundle.relevant_logs,
        *bundle.similar_incidents,
        *bundle.affected_assets,
        *runbooks,
    ]


class LLMQuestionAnswerer:
    """Answers incident questions with an LLM grounded in retrieved evidence.

    The model only sees the SQL evidence bundle and the retrieved runbook
    sections, must return a fixed schema, and any citation that does not
    match retrieved evidence is removed and reported as a limitation.
    """

    def __init__(
        self,
        structured_model=None,
        provider: str | None = None,
        runbook_search: Callable[[str], list[EvidenceRecord]] | None = None,
    ) -> None:
        if structured_model is None:  # pragma: no cover - needs a real LLM
            from assistant.llm.providers import get_chat_model

            structured_model = get_chat_model(provider).with_structured_output(
                LLMAnswer
            )

        self.model = structured_model
        self.runbook_search = runbook_search or default_runbook_search

    def answer(
        self,
        question: str,
        bundle: IncidentEvidenceBundle,
    ) -> InvestigationQuestionResponse:
        limitations = list(bundle.limitations)

        try:
            runbooks = self.runbook_search(
                build_runbook_query(question, bundle)
            )
        except Exception as error:  # noqa: BLE001 - answer without runbooks
            runbooks = []
            limitations.append(f"Runbook search unavailable: {error}")

        runbook_text = "\n\n".join(
            f"[{chunk.evidence_id}] {chunk.record.get('content', '')}"
            for chunk in runbooks
        )

        result: LLMAnswer = self.model.invoke(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    build_user_message(
                        question,
                        bundle.model_dump_json(),
                        runbook_text,
                    ),
                ),
            ]
        )

        valid_ids = {
            record.evidence_id for record in all_evidence(bundle, runbooks)
        }
        cleaned = [citation.strip(" []") for citation in result.citations]
        citations = list(dict.fromkeys(c for c in cleaned if c in valid_ids))

        removed = len(set(cleaned)) - len(citations)
        if removed:
            limitations.append(
                f"{removed} citation(s) removed: not found in the "
                "retrieved evidence."
            )

        return InvestigationQuestionResponse(
            incident_id=bundle.incident_id,
            question=question,
            answer=result.answer,
            response_type=result.response_type,
            confidence=result.confidence,
            citations=citations,
            limitations=limitations,
            refused=result.refused,
        )
