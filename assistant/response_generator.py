from typing import Any

from assistant.models import (
    EvidenceRecord,
    IncidentAssistantResponse,
    IncidentEvidenceBundle,
)


def cite(evidence: EvidenceRecord) -> str:
    return f"[{evidence.evidence_id}]"


def add_citation(
    citations: list[str],
    evidence: EvidenceRecord,
) -> None:
    if evidence.evidence_id not in citations:
        citations.append(evidence.evidence_id)


def extract_embedded_records(
    incident: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence = incident.get("evidence")

    if not isinstance(evidence, dict):
        return []

    records = evidence.get("records", [])

    if not isinstance(records, list):
        return []

    return [record for record in records if isinstance(record, dict)]


def extract_injection_evidence(
    incident: dict[str, Any],
) -> dict[str, Any]:
    evidence = incident.get("evidence")

    if not isinstance(evidence, dict):
        return {}

    injection_evidence = evidence.get("injection_evidence", {})

    if not isinstance(injection_evidence, dict):
        return {}

    return injection_evidence


class IncidentResponseGenerator:
    def generate(
        self,
        bundle: IncidentEvidenceBundle,
    ) -> IncidentAssistantResponse:
        incident_evidence = bundle.incident
        incident = incident_evidence.record
        incident_citation = cite(incident_evidence)

        citations: list[str] = []
        add_citation(citations, incident_evidence)

        incident_summary = self._build_summary(
            incident,
            incident_citation,
        )

        confirmed_evidence = self._build_confirmed_evidence(
            incident_evidence,
            bundle.failed_tests,
            bundle.relevant_logs,
            citations,
        )

        hypotheses = self._build_hypotheses(
            incident_evidence,
            bundle.similar_incidents,
            citations,
        )

        affected_assets = self._build_affected_assets(
            bundle.affected_assets,
            citations,
        )

        recommendations = self._build_recommendations(
            incident,
            bundle,
        )

        confidence = self._calculate_confidence(
            incident,
            bundle,
        )

        return IncidentAssistantResponse(
            incident_id=bundle.incident_id,
            incident_summary=incident_summary,
            confirmed_evidence=confirmed_evidence,
            likely_causes_or_hypotheses=hypotheses,
            affected_assets=affected_assets,
            recommended_investigation=recommendations,
            confidence=confidence,
            limitations=bundle.limitations,
            citations=citations,
        )

    def _build_summary(
        self,
        incident: dict[str, Any],
        citation: str,
    ) -> str:
        title = incident.get("title") or "Untitled incident"
        incident_type = incident.get("incident_type") or "unknown"
        severity = incident.get("severity") or "unknown"
        status = incident.get("status") or "unknown"
        affected_table = (
            incident.get("affected_table") or "an unspecified table"
        )
        description = (
            incident.get("description") or "No description was recorded."
        )

        return (
            f"{title} is a {severity}-severity "
            f"{incident_type} incident with status '{status}', "
            f"affecting {affected_table}. "
            f"{description} {citation}"
        )

    def _build_confirmed_evidence(
        self,
        incident_evidence: EvidenceRecord,
        failed_tests: list[EvidenceRecord],
        relevant_logs: list[EvidenceRecord],
        citations: list[str],
    ) -> list[str]:
        incident = incident_evidence.record
        incident_citation = cite(incident_evidence)

        evidence_items: list[str] = []

        failed_rule = incident.get("failed_rule")

        if failed_rule:
            evidence_items.append(
                f"The recorded failed rule was '{failed_rule}'. "
                f"{incident_citation}"
            )

        embedded_records = extract_embedded_records(incident)

        for record in embedded_records:
            source_file = (
                record.get("source_file") or "an unspecified source file"
            )
            row_number = record.get("source_row_number")
            failure_reason = (
                record.get("failure_reason")
                or record.get("failed_rule")
                or "an unspecified validation failure"
            )
            record_data = record.get("record_data", {})

            payment_id = None
            amount = None

            if isinstance(record_data, dict):
                payment_id = record_data.get("payment_id")
                amount = record_data.get("amount")

            details: list[str] = [
                f"source file {source_file}",
                f"failure reason '{failure_reason}'",
            ]

            if row_number is not None:
                details.append(f"source row {row_number}")

            if payment_id is not None:
                details.append(f"payment {payment_id}")

            if amount is not None:
                details.append(f"amount {amount}")

            evidence_items.append(
                "A quarantined record was captured with "
                + ", ".join(details)
                + f". {incident_citation}"
            )

        evidence_object = incident.get("evidence")

        if isinstance(evidence_object, dict):
            quarantined_count = evidence_object.get("quarantined_record_count")

            if quarantined_count is not None:
                evidence_items.append(
                    f"{quarantined_count} invalid record(s) were "
                    f"quarantined. {incident_citation}"
                )

        if incident.get("resolved_at"):
            resolution_notes = (
                incident.get("resolution_notes")
                or "No resolution notes were stored."
            )

            evidence_items.append(
                f"The incident was marked resolved at "
                f"{incident['resolved_at']}. Stored resolution notes: "
                f"{resolution_notes} {incident_citation}"
            )

        for test in failed_tests:
            record = test.record

            evidence_items.append(
                f"Quality test '{record.get('test_name')}' failed "
                f"with {record.get('records_failed')} failed "
                f"record(s). {cite(test)}"
            )

            add_citation(citations, test)

        for log in relevant_logs:
            record = log.record

            evidence_items.append(
                f"Airflow task '{record.get('task_id')}' recorded "
                f"status '{record.get('event_status')}' with error "
                f"'{record.get('error_message')}'. {cite(log)}"
            )

            add_citation(citations, log)

        if not evidence_items:
            evidence_items.append(
                "No confirmed technical evidence beyond the incident "
                f"record was available. {incident_citation}"
            )

        return evidence_items

    def _build_hypotheses(
        self,
        incident_evidence: EvidenceRecord,
        similar_incidents: list[EvidenceRecord],
        citations: list[str],
    ) -> list[str]:
        incident = incident_evidence.record
        incident_citation = cite(incident_evidence)

        hypotheses: list[str] = []

        injection_evidence = extract_injection_evidence(incident)

        if injection_evidence:
            change = injection_evidence.get("change")
            affected_file = injection_evidence.get("affected_file")
            affected_value = injection_evidence.get("affected_value")

            parts = []

            if change:
                parts.append(str(change))

            if affected_file:
                parts.append(f"file: {affected_file}")

            if affected_value:
                parts.append(f"record: {affected_value}")

            hypotheses.append(
                "The stored failure-injection evidence indicates "
                + "; ".join(parts)
                + f". This is recorded evidence, not an inferred "
                f"production root cause. {incident_citation}"
            )

        suspected_cause = incident.get("suspected_cause")

        if suspected_cause:
            hypotheses.append(
                f"The incident record lists this suspected cause: "
                f"{suspected_cause}. It remains a hypothesis unless "
                f"corroborated by additional evidence. "
                f"{incident_citation}"
            )

        strong_matches = [
            similar
            for similar in similar_incidents
            if int(similar.record.get("similarity_score", 0)) >= 3
        ]

        for similar in strong_matches[:3]:
            record = similar.record

            hypotheses.append(
                f"A related historical incident, "
                f"'{record.get('title')}', affected "
                f"{record.get('affected_table')} and has similarity "
                f"score {record.get('similarity_score')}. Its stored "
                f"resolution may be useful for comparison, but does "
                f"not prove the same root cause. {cite(similar)}"
            )

            add_citation(citations, similar)

        if not hypotheses:
            hypotheses.append(
                "The available evidence does not support a specific "
                "root-cause conclusion. Further investigation is "
                "required."
            )

        return hypotheses

    def _build_affected_assets(
        self,
        affected_assets: list[EvidenceRecord],
        citations: list[str],
    ) -> list[str]:
        if not affected_assets:
            return [
                "No downstream impacted assets were recorded. "
                "This means impact is unknown, not necessarily absent."
            ]

        results: list[str] = []

        for asset in affected_assets:
            record = asset.record

            owner = record.get("owner_name") or "unassigned"
            path = record.get("impact_path") or "not recorded"

            results.append(
                f"{record.get('unique_name')} "
                f"({record.get('asset_type')}), impact depth "
                f"{record.get('impact_depth')}, owner {owner}, "
                f"path {path}. {cite(asset)}"
            )

            add_citation(citations, asset)

        return results

    def _build_recommendations(
        self,
        incident: dict[str, Any],
        bundle: IncidentEvidenceBundle,
    ) -> list[str]:
        recommendations = [
            "Verify the source record and source file against the "
            "producer system before changing pipeline logic.",
            "Review the quarantined record and confirm that the "
            "validation rule behaved as intended.",
        ]

        if not bundle.relevant_logs:
            recommendations.append(
                "Correlate the incident with raw Airflow task logs if "
                "a DAG run identifier becomes available."
            )

        if not bundle.failed_tests:
            recommendations.append(
                "Confirm that the rejected record did not reach dbt "
                "models; no directly related failed dbt test is "
                "currently stored."
            )

        if not bundle.affected_assets:
            recommendations.append(
                "Run or review lineage-impact traversal before "
                "concluding that no downstream KPI was affected."
            )

        if incident.get("status", "").lower() == "resolved":
            recommendations.append(
                "Review the stored resolution notes and verify the "
                "clean baseline with a successful idempotent rerun."
            )

        return recommendations

    def _calculate_confidence(
        self,
        incident: dict[str, Any],
        bundle: IncidentEvidenceBundle,
    ) -> str:
        score = 0

        if incident.get("evidence"):
            score += 2

        if incident.get("failed_rule"):
            score += 1

        if bundle.failed_tests:
            score += 1

        if bundle.relevant_logs:
            score += 1

        if bundle.affected_assets:
            score += 1

        if score >= 5:
            return "high"

        if score >= 2:
            return "medium"

        return "low"
