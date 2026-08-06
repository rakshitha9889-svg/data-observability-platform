from assistant.models import (
    IncidentAssistantResponse,
    IncidentEvidenceBundle,
    InvestigationQuestionResponse,
)


class IncidentQuestionAnswerer:
    def answer(
        self,
        question: str,
        bundle: IncidentEvidenceBundle,
        investigation: IncidentAssistantResponse,
    ) -> InvestigationQuestionResponse:
        normalized_question = question.lower().strip()

        if self._contains_any(
            normalized_question,
            [
                "summary",
                "summarize",
                "what happened",
                "describe incident",
                "describe this incident",
                "incident about",
            ],
        ):
            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=investigation.incident_summary,
                response_type="incident_summary",
                citations=investigation.citations[:1],
            )

        if self._contains_any(
            normalized_question,
            [
                "cause",
                "root cause",
                "why",
                "reason",
                "hypothesis",
            ],
        ):
            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=self._join_items(
                    investigation.likely_causes_or_hypotheses
                ),
                response_type="cause_or_hypothesis",
                citations=investigation.citations,
            )

        if self._contains_any(
            normalized_question,
            [
                "affected",
                "impact",
                "downstream",
                "asset",
                "kpi",
                "dashboard",
                "owner",
            ],
        ):
            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=self._join_items(investigation.affected_assets),
                response_type="affected_assets",
                citations=[
                    item.evidence_id for item in bundle.affected_assets
                ],
            )

        if self._contains_any(
            normalized_question,
            [
                "evidence",
                "proof",
                "confirm",
                "record",
                "quarantine",
                "amount",
                "payment",
                "source file",
                "failed rule",
            ],
        ):
            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=self._join_items(investigation.confirmed_evidence),
                response_type="confirmed_evidence",
                citations=investigation.citations,
            )

        if self._contains_any(
            normalized_question,
            [
                "recommend",
                "investigate",
                "next step",
                "what should",
                "fix",
                "how to resolve",
                "remediation",
            ],
        ):
            answer = self._join_items(investigation.recommended_investigation)

            answer += (
                " These are recommendations only. "
                "The assistant has not executed any remediation."
            )

            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=answer,
                response_type="recommended_investigation",
                citations=[],
            )

        if self._contains_any(
            normalized_question,
            [
                "status",
                "severity",
                "detected",
                "resolved",
                "resolution",
            ],
        ):
            incident = bundle.incident.record
            citation = bundle.incident.evidence_id

            answer = (
                f"The incident status is "
                f"'{incident.get('status', 'unknown')}' and its "
                f"severity is "
                f"'{incident.get('severity', 'unknown')}'. "
                f"It was detected at "
                f"{incident.get('detected_at', 'an unknown time')} "
                f"and resolved at "
                f"{incident.get('resolved_at') or 'not resolved'}. "
                f"[{citation}]"
            )

            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=answer,
                response_type="status",
                citations=[citation],
            )

        if self._contains_any(
            normalized_question,
            [
                "dbt",
                "test",
                "quality test",
            ],
        ):
            if not bundle.failed_tests:
                answer = (
                    "No directly related failed dbt or quality-test "
                    "records were retrieved for this incident. "
                    "The incident was detected by ingestion validation, "
                    "so absence of a dbt failure is expected."
                )

                citations = [bundle.incident.evidence_id]

            else:
                answer = self._join_items(investigation.confirmed_evidence)

                citations = [item.evidence_id for item in bundle.failed_tests]

            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=answer,
                response_type="quality_tests",
                citations=citations,
            )

        if self._contains_any(
            normalized_question,
            [
                "airflow",
                "task",
                "dag",
                "log",
            ],
        ):
            if not bundle.relevant_logs:
                answer = (
                    "No directly relevant Airflow task event was "
                    "retrieved. The assistant will not attach unrelated "
                    "failed tasks to this incident."
                )
                citations: list[str] = []

            else:
                messages = []

                for log in bundle.relevant_logs:
                    record = log.record

                    messages.append(
                        f"Task {record.get('task_id')} recorded "
                        f"{record.get('event_status')}: "
                        f"{record.get('error_message')} "
                        f"[{log.evidence_id}]"
                    )

                answer = self._join_items(messages)

                citations = [item.evidence_id for item in bundle.relevant_logs]

            return self._create_response(
                question=question,
                bundle=bundle,
                investigation=investigation,
                answer=answer,
                response_type="airflow_logs",
                citations=citations,
            )

        return InvestigationQuestionResponse(
            incident_id=bundle.incident_id,
            question=question,
            answer=(
                "I cannot answer this question from the permitted "
                "incident evidence. Ask about the incident summary, "
                "confirmed evidence, likely cause, affected assets, "
                "quality tests, Airflow logs, status or recommended "
                "investigation."
            ),
            response_type="unsupported",
            confidence="low",
            citations=[],
            limitations=bundle.limitations,
            refused=True,
        )

    def _create_response(
        self,
        question: str,
        bundle: IncidentEvidenceBundle,
        investigation: IncidentAssistantResponse,
        answer: str,
        response_type: str,
        citations: list[str],
    ) -> InvestigationQuestionResponse:
        unique_citations = list(dict.fromkeys(citations))

        return InvestigationQuestionResponse(
            incident_id=bundle.incident_id,
            question=question,
            answer=answer,
            response_type=response_type,
            confidence=investigation.confidence,
            citations=unique_citations,
            limitations=bundle.limitations,
            refused=False,
        )

    @staticmethod
    def _contains_any(
        question: str,
        phrases: list[str],
    ) -> bool:
        return any(phrase in question for phrase in phrases)

    @staticmethod
    def _join_items(
        items: list[str],
    ) -> str:
        if not items:
            return "No supported evidence was available."

        return " ".join(items)
