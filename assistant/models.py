from typing import Any

from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    evidence_id: str
    source_table: str
    record: dict[str, Any]


class IncidentEvidenceBundle(BaseModel):
    incident_id: str
    incident: EvidenceRecord
    failed_tests: list[EvidenceRecord] = Field(default_factory=list)
    relevant_logs: list[EvidenceRecord] = Field(default_factory=list)
    similar_incidents: list[EvidenceRecord] = Field(default_factory=list)
    affected_assets: list[EvidenceRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class IncidentAssistantResponse(BaseModel):
    incident_id: str
    incident_summary: str
    confirmed_evidence: list[str] = Field(default_factory=list)
    likely_causes_or_hypotheses: list[str] = Field(default_factory=list)
    affected_assets: list[str] = Field(default_factory=list)
    recommended_investigation: list[str] = Field(default_factory=list)
    confidence: str
    limitations: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


class InvestigationQuestionRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=500,
    )


class InvestigationQuestionResponse(BaseModel):
    incident_id: str
    question: str
    answer: str
    response_type: str
    confidence: str
    citations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    refused: bool = False
