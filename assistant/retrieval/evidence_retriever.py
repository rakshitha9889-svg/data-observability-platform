from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from assistant.config import get_settings
from assistant.models import EvidenceRecord, IncidentEvidenceBundle
from assistant.retrieval.database import fetch_all, fetch_one


def make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return float(value)

    return value


def create_evidence_record(
    source_table: str,
    primary_key: str,
    record: dict[str, Any],
) -> EvidenceRecord:
    identifier = record.get(primary_key)

    return EvidenceRecord(
        evidence_id=f"{source_table}:{identifier}",
        source_table=source_table,
        record=make_json_safe(record),
    )


class IncidentEvidenceRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()

    def retrieve_incident(
        self,
        incident_id: str,
    ) -> dict[str, Any] | None:
        return fetch_one(
            """
            SELECT
                incident_id,
                run_id,
                test_result_id,
                experiment_id,
                incident_type,
                severity,
                status,
                source,
                affected_entity,
                affected_table,
                title,
                description,
                failed_rule,
                evidence,
                suspected_cause,
                resolution_notes,
                detected_at,
                acknowledged_at,
                resolved_at,
                created_at,
                updated_at
            FROM observability.incidents
            WHERE incident_id = CAST(:incident_id AS UUID);
            """,
            {"incident_id": incident_id},
        )

    def retrieve_failed_tests(
        self,
        incident: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return fetch_all(
            """
            SELECT
                quality.test_result_id,
                quality.run_id,
                quality.test_name,
                quality.test_type,
                quality.entity_name,
                quality.table_name,
                quality.column_name,
                quality.status,
                quality.severity,
                quality.records_checked,
                quality.records_failed,
                quality.failure_message,
                quality.evidence,
                quality.executed_at
            FROM observability.quality_test_results AS quality
            WHERE LOWER(quality.status) = 'failed'
              AND (
                    quality.test_result_id = :test_result_id
                    OR quality.run_id = :run_id
                    OR (
                        :affected_table IS NOT NULL
                        AND quality.table_name = :affected_table
                    )
                    OR (
                        :failed_rule IS NOT NULL
                        AND quality.test_name = :failed_rule
                    )
              )
            ORDER BY quality.executed_at DESC
            LIMIT :result_limit;
            """,
            {
                "test_result_id": incident.get("test_result_id"),
                "run_id": incident.get("run_id"),
                "affected_table": incident.get("affected_table"),
                "failed_rule": incident.get("failed_rule"),
                "result_limit": self.settings.maximum_failed_tests,
            },
        )

    def retrieve_relevant_logs(
        self,
        incident: dict[str, Any],
    ) -> list[dict[str, Any]]:
        affected_table = incident.get("affected_table") or ""
        affected_entity = incident.get("affected_entity") or ""
        failed_rule = incident.get("failed_rule") or ""
        incident_title = incident.get("title") or ""

        search_terms = [
            affected_table,
            affected_entity,
            failed_rule,
            incident_title,
        ]

        search_terms = [
            term.strip() for term in search_terms if term and term.strip()
        ]

        if not search_terms:
            return []

        return fetch_all(
            """
            SELECT
                event_id,
                dag_id,
                task_id,
                dag_run_id,
                event_status,
                try_number,
                logical_date,
                event_time,
                error_type,
                error_message,
                created_at
            FROM observability.airflow_task_events
            WHERE
                event_time BETWEEN
                    CAST(:detected_at AS TIMESTAMPTZ)
                        - INTERVAL '15 minutes'
                    AND
                    CAST(:detected_at AS TIMESTAMPTZ)
                        + INTERVAL '15 minutes'
                AND (
                    COALESCE(error_message, '') ILIKE
                        :table_pattern
                    OR COALESCE(error_message, '') ILIKE
                        :entity_pattern
                    OR COALESCE(error_message, '') ILIKE
                        :rule_pattern
                    OR COALESCE(error_message, '') ILIKE
                        :title_pattern
                )
            ORDER BY event_time DESC
            LIMIT :result_limit;
            """,
            {
                "detected_at": incident["detected_at"],
                "table_pattern": f"%{affected_table}%",
                "entity_pattern": f"%{affected_entity}%",
                "rule_pattern": f"%{failed_rule}%",
                "title_pattern": f"%{incident_title}%",
                "result_limit": self.settings.maximum_logs,
            },
        )

    def retrieve_similar_incidents(
        self,
        incident: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return fetch_all(
            """
            SELECT
                incident_id,
                incident_type,
                severity,
                status,
                affected_table,
                title,
                description,
                failed_rule,
                suspected_cause,
                resolution_notes,
                detected_at,
                resolved_at,

                (
                    CASE
                        WHEN failed_rule = :failed_rule THEN 5
                        ELSE 0
                    END
                    +
                    CASE
                        WHEN affected_table = :affected_table THEN 3
                        ELSE 0
                    END
                    +
                    CASE
                        WHEN incident_type = :incident_type THEN 1
                        ELSE 0
                    END
                ) AS similarity_score
            FROM observability.incidents
            WHERE incident_id <> :incident_id
              AND (
                    failed_rule = :failed_rule
                    OR affected_table = :affected_table
                    OR incident_type = :incident_type
              )
            ORDER BY
                similarity_score DESC,
                CASE
                    WHEN LOWER(status) = 'resolved' THEN 0
                    ELSE 1
                END,
                detected_at DESC
            LIMIT :result_limit;
            """,
            {
                "incident_id": incident["incident_id"],
                "incident_type": incident.get("incident_type"),
                "affected_table": incident.get("affected_table"),
                "failed_rule": incident.get("failed_rule"),
                "result_limit": self.settings.maximum_similar_incidents,
            },
        )

    def retrieve_affected_assets(
        self,
        incident_id: str,
    ) -> list[dict[str, Any]]:
        return fetch_all(
            """
            SELECT
                impact.incident_id,
                asset.asset_id,
                asset.unique_name,
                asset.asset_type,
                asset.database_name,
                asset.schema_name,
                asset.object_name,
                asset.owner_name,
                asset.description,
                impact.impact_depth,
                impact.impact_path,
                impact.recorded_at
            FROM observability.incident_impacted_assets AS impact
            JOIN observability.lineage_assets AS asset
              ON asset.asset_id = impact.asset_id
            WHERE impact.incident_id = CAST(:incident_id AS UUID)
            ORDER BY
                impact.impact_depth,
                asset.unique_name
            LIMIT :result_limit;
            """,
            {
                "incident_id": incident_id,
                "result_limit": self.settings.maximum_affected_assets,
            },
        )

    def build_evidence_bundle(
        self,
        incident_id: str,
    ) -> IncidentEvidenceBundle:
        incident = self.retrieve_incident(incident_id)

        if incident is None:
            raise ValueError(f"Incident does not exist: {incident_id}")

        failed_tests = self.retrieve_failed_tests(incident)
        relevant_logs = self.retrieve_relevant_logs(incident)
        similar_incidents = self.retrieve_similar_incidents(incident)
        affected_assets = self.retrieve_affected_assets(incident_id)

        limitations: list[str] = []

        if not failed_tests:
            limitations.append(
                "No directly related failed quality-test records were found."
            )

        if not relevant_logs:
            limitations.append("No relevant Airflow error logs were found.")

        if not similar_incidents:
            limitations.append("No similar historical incidents were found.")

        if not affected_assets:
            limitations.append("No downstream impacted assets were recorded.")

        return IncidentEvidenceBundle(
            incident_id=incident_id,
            incident=create_evidence_record(
                "observability.incidents",
                "incident_id",
                incident,
            ),
            failed_tests=[
                create_evidence_record(
                    "observability.quality_test_results",
                    "test_result_id",
                    record,
                )
                for record in failed_tests
            ],
            relevant_logs=[
                create_evidence_record(
                    "observability.airflow_task_events",
                    "event_id",
                    record,
                )
                for record in relevant_logs
            ],
            similar_incidents=[
                create_evidence_record(
                    "observability.incidents",
                    "incident_id",
                    record,
                )
                for record in similar_incidents
            ],
            affected_assets=[
                create_evidence_record(
                    "observability.lineage_assets",
                    "asset_id",
                    record,
                )
                for record in affected_assets
            ],
            limitations=limitations,
        )
