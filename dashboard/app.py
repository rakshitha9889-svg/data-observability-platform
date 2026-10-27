import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from database import clear_query_cache, execute_query, test_connection

ASSISTANT_API_URL = os.getenv(
    "ASSISTANT_API_URL",
    "http://localhost:8000",
)


def call_assistant_api(
    endpoint: str,
) -> dict:
    url = f"{ASSISTANT_API_URL}{endpoint}"

    try:
        response = requests.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    except requests.ConnectionError as error:
        raise RuntimeError(
            "The incident-assistant API is unavailable. "
            "Start FastAPI on port 8000."
        ) from error

    except requests.Timeout as error:
        raise RuntimeError(
            "The incident-assistant API request timed out."
        ) from error

    except requests.HTTPError as error:
        detail = response.text

        raise RuntimeError(
            f"Assistant API returned an error: {detail}"
        ) from error

def post_assistant_api(
    endpoint: str,
    payload: dict,
) -> dict:
    url = f"{ASSISTANT_API_URL}{endpoint}"

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    except requests.ConnectionError as error:
        raise RuntimeError(
            "The incident-assistant API is unavailable. "
            "Start FastAPI on port 8000."
        ) from error

    except requests.Timeout as error:
        raise RuntimeError(
            "The incident-assistant API request timed out."
        ) from error

    except requests.HTTPError as error:
        raise RuntimeError(
            f"Assistant API returned an error: {response.text}"
        ) from error

@st.cache_data(ttl=15)
def load_assistant_incidents() -> list[dict]:
    payload = call_assistant_api(
        "/api/v1/incidents?limit=100"
    )

    return payload.get("incidents", [])

st.set_page_config(
    page_title="Data Observability Platform",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        [data-testid="stMetric"] {
            background-color: #f7f9fc;
            border: 1px solid #dce3ed;
            border-radius: 10px;
            padding: 15px;
        }

        [data-testid="stMetricLabel"] {
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_overview() -> None:
    st.header("Platform Overview")

    metrics = execute_query(
        """
        SELECT
            COUNT(*) AS total_runs,

            COUNT(*) FILTER (
                WHERE LOWER(status) = 'succeeded'
            ) AS successful_runs,

            ROUND(
                100.0
                * COUNT(*) FILTER (
                    WHERE LOWER(status) = 'succeeded'
                )
                / NULLIF(COUNT(*), 0),
                2
            ) AS pipeline_success_rate,

            MAX(completed_at) AS latest_pipeline_completion,

            ROUND(
                EXTRACT(
                    EPOCH FROM (
                        CURRENT_TIMESTAMP - MAX(completed_at)
                    )
                ) / 3600.0,
                2
            ) AS freshness_hours
        FROM observability.pipeline_runs;
        """
    ).iloc[0]

    quality_metrics = execute_query(
        """
        SELECT
            COUNT(*) AS total_tests,

            COUNT(*) FILTER (
                WHERE LOWER(status) = 'passed'
            ) AS passed_tests,

            COUNT(*) FILTER (
                WHERE LOWER(status) = 'failed'
            ) AS failed_tests,

            ROUND(
                100.0
                * COUNT(*) FILTER (
                    WHERE LOWER(status) = 'passed'
                )
                / NULLIF(COUNT(*), 0),
                2
            ) AS test_pass_rate
        FROM observability.quality_test_results;
        """
    ).iloc[0]

    incident_metrics = execute_query(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE LOWER(status) = 'open'
            ) AS open_incidents,

            COUNT(*) FILTER (
                WHERE LOWER(status) = 'resolved'
            ) AS resolved_incidents,

            ROUND(
                AVG(
                    EXTRACT(
                        EPOCH FROM (resolved_at - detected_at)
                    )
                ) FILTER (
                    WHERE resolved_at IS NOT NULL
                      AND detected_at IS NOT NULL
                ) / 60.0,
                2
            ) AS mttr_minutes
        FROM observability.incidents;
        """
    ).iloc[0]

    column_1, column_2, column_3, column_4, column_5 = st.columns(5)

    column_1.metric(
        "Pipeline Success Rate",
        f"{float(metrics['pipeline_success_rate'] or 0):.1f}%",
        help="Percentage of pipeline runs with succeeded status.",
    )

    column_2.metric(
        "Test Pass Rate",
        f"{float(quality_metrics['test_pass_rate'] or 0):.1f}%",
        help="Percentage of stored data-quality tests that passed.",
    )

    column_3.metric(
        "Open Incidents",
        int(incident_metrics["open_incidents"] or 0),
        help="Incidents that have not yet been resolved.",
    )

    column_4.metric(
        "MTTR",
        f"{float(incident_metrics['mttr_minutes'] or 0):.1f} min",
        help="Mean time to resolution for resolved incidents.",
    )

    column_5.metric(
        "Data Freshness",
        f"{float(metrics['freshness_hours'] or 0):.1f} h",
        help="Hours since the latest completed pipeline run.",
    )

    st.divider()

    left_column, right_column = st.columns(2)

    pipeline_status = execute_query(
        """
        SELECT
            status,
            COUNT(*) AS run_count
        FROM observability.pipeline_runs
        GROUP BY status
        ORDER BY run_count DESC;
        """
    )

    pipeline_figure = px.pie(
        pipeline_status,
        names="status",
        values="run_count",
        title="Pipeline Runs by Status",
        hole=0.45,
        color="status",
        color_discrete_map={
            "succeeded": "#16a34a",
            "partially_succeeded": "#f59e0b",
            "failed": "#dc2626",
        },
    )

    left_column.plotly_chart(
        pipeline_figure,
        use_container_width=True,
    )

    test_status = execute_query(
        """
        SELECT
            status,
            COUNT(*) AS test_count
        FROM observability.quality_test_results
        GROUP BY status
        ORDER BY test_count DESC;
        """
    )

    test_figure = px.bar(
        test_status,
        x="status",
        y="test_count",
        title="Data-Quality Test Results",
        color="status",
        color_discrete_map={
            "passed": "#16a34a",
            "failed": "#dc2626",
        },
        text_auto=True,
    )

    right_column.plotly_chart(
        test_figure,
        use_container_width=True,
    )

    st.subheader("Recent Incidents")

    recent_incidents = execute_query(
        """
        SELECT
            incident_type,
            severity,
            status,
            affected_table,
            failed_rule,
            detected_at,
            resolved_at
        FROM observability.incidents
        ORDER BY detected_at DESC
        LIMIT 10;
        """
    )

    st.dataframe(
        recent_incidents,
        use_container_width=True,
        hide_index=True,
    )


def show_pipeline_runs() -> None:
    st.header("Pipeline Runs")

    pipeline_runs = execute_query(
        """
        SELECT
            run_id,
            pipeline_name,
            batch_date,
            status,
            started_at,
            completed_at,

            ROUND(
                EXTRACT(
                    EPOCH FROM (completed_at - started_at)
                )::numeric,
                2
            ) AS duration_seconds,

            files_discovered,
            files_processed,
            files_succeeded,
            files_failed,
            files_skipped,
            rows_received,
            rows_loaded,
            rows_rejected,
            error_type,
            error_message
        FROM observability.pipeline_runs
        ORDER BY started_at DESC;
        """
    )

    if pipeline_runs.empty:
        st.info("No pipeline runs are currently stored.")
        return

    available_statuses = sorted(
        pipeline_runs["status"].dropna().unique().tolist()
    )

    selected_statuses = st.multiselect(
        "Filter by pipeline status",
        available_statuses,
        default=available_statuses,
    )

    filtered_runs = pipeline_runs[
        pipeline_runs["status"].isin(selected_statuses)
    ]

    total_rows_loaded = filtered_runs["rows_loaded"].fillna(0).sum()
    total_rows_rejected = filtered_runs["rows_rejected"].fillna(0).sum()
    average_duration = filtered_runs["duration_seconds"].dropna().mean()

    column_1, column_2, column_3 = st.columns(3)

    column_1.metric(
        "Rows Loaded",
        f"{int(total_rows_loaded):,}",
    )

    column_2.metric(
        "Rows Rejected",
        f"{int(total_rows_rejected):,}",
    )

    column_3.metric(
        "Average Duration",
        (
            f"{average_duration:.2f} sec"
            if pd.notna(average_duration)
            else "N/A"
        ),
    )

    trend_data = filtered_runs.dropna(
        subset=["started_at", "duration_seconds"]
    )

    if not trend_data.empty:
        duration_figure = px.line(
            trend_data.sort_values("started_at"),
            x="started_at",
            y="duration_seconds",
            color="status",
            markers=True,
            title="Pipeline Duration Trend",
            labels={
                "started_at": "Run start time",
                "duration_seconds": "Duration in seconds",
            },
        )

        st.plotly_chart(
            duration_figure,
            use_container_width=True,
        )

    st.subheader("Run Details")

    st.dataframe(
        filtered_runs,
        use_container_width=True,
        hide_index=True,
    )


def show_data_quality() -> None:
    st.header("Data Quality")

    quality_results = execute_query(
        """
        SELECT
            test_result_id,
            test_name,
            test_type,
            entity_name,
            table_name,
            column_name,
            status,
            severity,
            records_checked,
            records_failed,
            failure_message,
            executed_at
        FROM observability.quality_test_results
        ORDER BY executed_at DESC;
        """
    )

    if quality_results.empty:
        st.info("No data-quality test results are currently stored.")
        return

    total_tests = len(quality_results)

    failed_tests = int(
        quality_results["status"]
        .str.lower()
        .eq("failed")
        .sum()
    )

    failed_records = int(
        quality_results["records_failed"]
        .fillna(0)
        .sum()
    )

    tested_tables = quality_results["table_name"].nunique()

    column_1, column_2, column_3, column_4 = st.columns(4)

    column_1.metric("Executed Tests", f"{total_tests:,}")
    column_2.metric("Failed Tests", f"{failed_tests:,}")
    column_3.metric("Failed Records", f"{failed_records:,}")
    column_4.metric("Tables Covered", tested_tables)

    failures_by_table = execute_query(
        """
        SELECT
            COALESCE(table_name, entity_name, 'unknown') AS affected_table,
            COUNT(*) AS failed_tests,
            SUM(COALESCE(records_failed, 0)) AS failed_records
        FROM observability.quality_test_results
        WHERE LOWER(status) = 'failed'
        GROUP BY COALESCE(table_name, entity_name, 'unknown')
        ORDER BY failed_tests DESC;
        """
    )

    failures_by_rule = execute_query(
        """
        SELECT
            test_name,
            COUNT(*) AS failure_count,
            SUM(COALESCE(records_failed, 0)) AS failed_records
        FROM observability.quality_test_results
        WHERE LOWER(status) = 'failed'
        GROUP BY test_name
        ORDER BY failure_count DESC
        LIMIT 15;
        """
    )

    left_column, right_column = st.columns(2)

    if not failures_by_table.empty:
        table_figure = px.bar(
            failures_by_table,
            x="affected_table",
            y="failed_tests",
            color="failed_records",
            title="Failures by Table",
            text_auto=True,
            labels={
                "affected_table": "Table",
                "failed_tests": "Failed tests",
                "failed_records": "Failed records",
            },
        )

        left_column.plotly_chart(
            table_figure,
            use_container_width=True,
        )

    if not failures_by_rule.empty:
        rule_figure = px.bar(
            failures_by_rule,
            x="failure_count",
            y="test_name",
            orientation="h",
            title="Most Frequently Failing Rules",
            color="failed_records",
            labels={
                "failure_count": "Failure count",
                "test_name": "Test",
            },
        )

        rule_figure.update_layout(
            yaxis={"categoryorder": "total ascending"}
        )

        right_column.plotly_chart(
            rule_figure,
            use_container_width=True,
        )

    quarantine_results = execute_query(
        """
        SELECT
            quarantine_id,
            entity_name,
            source_file,
            source_row_number,
            failed_rule,
            failure_type,
            failure_reason,
            severity,
            quarantined_at,
            resolved
        FROM quarantine.invalid_records
        ORDER BY quarantined_at DESC;
        """
    )

    st.subheader("Quarantined Records")

    unresolved_only = st.checkbox(
        "Show only unresolved quarantined records",
        value=False,
    )

    if unresolved_only:
        quarantine_results = quarantine_results[
            quarantine_results["resolved"].fillna(False).eq(False)
        ]

    st.dataframe(
        quarantine_results,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Failed Test Evidence")

    failed_result_details = quality_results[
        quality_results["status"].str.lower().eq("failed")
    ]

    st.dataframe(
        failed_result_details,
        use_container_width=True,
        hide_index=True,
    )


def show_incidents() -> None:
    st.header("Incident Management")

    incidents = execute_query(
        """
        SELECT
            incident_id,
            incident_type,
            severity,
            status,
            source,
            affected_entity,
            affected_table,
            title,
            description,
            failed_rule,
            suspected_cause,
            resolution_notes,
            detected_at,
            acknowledged_at,
            resolved_at,

            ROUND(
                EXTRACT(
                    EPOCH FROM (resolved_at - detected_at)
                )::numeric / 60.0,
                2
            ) AS resolution_minutes
        FROM observability.incidents
        ORDER BY detected_at DESC;
        """
    )

    if incidents.empty:
        st.info("No incidents are currently stored.")
        return

    open_count = int(
        incidents["status"].str.lower().eq("open").sum()
    )

    resolved_count = int(
        incidents["status"].str.lower().eq("resolved").sum()
    )

    critical_high_count = int(
        incidents["severity"]
        .str.lower()
        .isin(["critical", "high"])
        .sum()
    )

    mttr = incidents["resolution_minutes"].dropna().mean()

    column_1, column_2, column_3, column_4 = st.columns(4)

    column_1.metric("Open Incidents", open_count)
    column_2.metric("Resolved Incidents", resolved_count)
    column_3.metric("Critical/High", critical_high_count)

    column_4.metric(
        "MTTR",
        f"{mttr:.2f} min" if pd.notna(mttr) else "N/A",
    )

    selected_status = st.multiselect(
        "Filter by incident status",
        sorted(incidents["status"].dropna().unique()),
        default=sorted(incidents["status"].dropna().unique()),
    )

    selected_severity = st.multiselect(
        "Filter by severity",
        sorted(incidents["severity"].dropna().unique()),
        default=sorted(incidents["severity"].dropna().unique()),
    )

    filtered_incidents = incidents[
        incidents["status"].isin(selected_status)
        & incidents["severity"].isin(selected_severity)
    ]

    severity_counts = (
        filtered_incidents.groupby(
            ["severity", "status"],
            dropna=False,
        )
        .size()
        .reset_index(name="incident_count")
    )

    if not severity_counts.empty:
        severity_figure = px.bar(
            severity_counts,
            x="severity",
            y="incident_count",
            color="status",
            barmode="group",
            title="Incidents by Severity and Status",
            text_auto=True,
            color_discrete_map={
                "open": "#dc2626",
                "resolved": "#16a34a",
            },
        )

        st.plotly_chart(
            severity_figure,
            use_container_width=True,
        )

    st.subheader("Incident Records")

    st.dataframe(
        filtered_incidents,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Investigate an Incident")

    incident_options = {
        f"{row['severity']} | {row['status']} | {row['title']}":
            row["incident_id"]
        for _, row in filtered_incidents.iterrows()
    }

    if incident_options:
        selected_label = st.selectbox(
            "Select an incident",
            list(incident_options.keys()),
        )

        selected_incident_id = incident_options[selected_label]

        incident_detail = filtered_incidents[
            filtered_incidents["incident_id"]
            == selected_incident_id
        ].iloc[0]

        st.write("**Description**")
        st.write(
            incident_detail["description"]
            or "No description available."
        )

        st.write("**Failed rule**")
        st.code(
            incident_detail["failed_rule"]
            or "No failed rule recorded."
        )

        st.write("**Suspected cause**")
        st.write(
            incident_detail["suspected_cause"]
            or "Not yet recorded."
        )

        st.write("**Resolution notes**")
        st.write(
            incident_detail["resolution_notes"]
            or "Incident is not yet resolved."
        )


def show_lineage() -> None:
    st.header("Lineage and Impact Analysis")

    lineage_summary = execute_query(
        """
        SELECT
            asset_type,
            COUNT(*) AS asset_count
        FROM observability.lineage_assets
        GROUP BY asset_type
        ORDER BY asset_count DESC;
        """
    )

    lineage_edges = execute_query(
        """
        SELECT
            upstream.unique_name AS upstream_asset,
            upstream.asset_type AS upstream_type,
            downstream.unique_name AS downstream_asset,
            downstream.asset_type AS downstream_type,
            edge.edge_type,
            edge.source_system
        FROM observability.lineage_edges AS edge
        JOIN observability.lineage_assets AS upstream
          ON upstream.asset_id = edge.upstream_asset_id
        JOIN observability.lineage_assets AS downstream
          ON downstream.asset_id = edge.downstream_asset_id
        ORDER BY upstream.unique_name, downstream.unique_name;
        """
    )

    impacted_assets = execute_query(
        """
        SELECT
            incident.incident_id,
            incident.title AS incident_title,
            incident.severity,
            incident.status,
            asset.unique_name AS impacted_asset,
            asset.asset_type,
            asset.owner_name,
            impact.impact_depth,
            impact.impact_path
        FROM observability.incident_impacted_assets AS impact
        JOIN observability.incidents AS incident
          ON incident.incident_id = impact.incident_id
        JOIN observability.lineage_assets AS asset
          ON asset.asset_id = impact.asset_id
        ORDER BY
            incident.detected_at DESC,
            impact.impact_depth,
            asset.unique_name;
        """
    )

    total_assets = (
        int(lineage_summary["asset_count"].sum())
        if not lineage_summary.empty
        else 0
    )

    total_edges = len(lineage_edges)
    total_impacted_assets = len(impacted_assets)

    column_1, column_2, column_3 = st.columns(3)

    column_1.metric("Registered Assets", total_assets)
    column_2.metric("Lineage Relationships", total_edges)
    column_3.metric("Recorded Impacts", total_impacted_assets)

    if not lineage_summary.empty:
        asset_figure = px.bar(
            lineage_summary,
            x="asset_type",
            y="asset_count",
            title="Assets by Type",
            color="asset_type",
            text_auto=True,
        )

        st.plotly_chart(
            asset_figure,
            use_container_width=True,
        )

    st.subheader("Dependency Relationships")

    st.dataframe(
        lineage_edges,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Incident Impact")

    if impacted_assets.empty:
        st.info(
            "No incident-to-asset impact records are currently stored."
        )
    else:
        st.dataframe(
            impacted_assets,
            use_container_width=True,
            hide_index=True,
        )

def show_assistant() -> None:
    st.header("Evidence-Grounded Incident Assistant")


    st.caption(
        "Investigate incidents using stored incident records, "
        "quality tests, Airflow events, historical resolutions "
        "and lineage evidence."
    )

    try:
        incidents = load_assistant_incidents()

    except RuntimeError as error:
        st.error(str(error))

        st.code(
            "python -m uvicorn "
            "assistant.api.main:app "
            "--host 0.0.0.0 "
            "--port 8000 "
            "--reload"
        )

        return

    if not incidents:
        st.info("No incidents are available for investigation.")
        return

    incident_options: dict[str, str] = {}

    for incident in incidents:
        incident_id = incident["incident_id"]

        label = (
            f"{incident.get('severity', 'unknown').upper()} | "
            f"{incident.get('status', 'unknown')} | "
            f"{incident.get('title', 'Untitled incident')} | "
            f"{incident_id}"
        )

        incident_options[label] = incident_id

    selected_label = st.selectbox(
        "Select an incident",
        options=list(incident_options.keys()),
    )

    selected_incident_id = incident_options[selected_label]

    if st.button(
        "Investigate Incident",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner(
            "Retrieving and analysing stored evidence..."
        ):
            try:
                investigation = call_assistant_api(
                    (
                        f"/api/v1/incidents/"
                        f"{selected_incident_id}/investigation"
                    )
                )

                evidence_bundle = call_assistant_api(
                    (
                        f"/api/v1/incidents/"
                        f"{selected_incident_id}/evidence"
                    )
                )

            except RuntimeError as error:
                st.error(str(error))
                return

        st.session_state["investigation"] = investigation
        st.session_state["evidence_bundle"] = evidence_bundle
        st.session_state["investigated_incident_id"] = (
            selected_incident_id
        )

    investigation = st.session_state.get("investigation")
    evidence_bundle = st.session_state.get("evidence_bundle")
    investigated_incident_id = st.session_state.get(
        "investigated_incident_id"
    )

    if (
        not investigation
        or investigated_incident_id != selected_incident_id
    ):
        st.info(
            "Select an incident and click "
            "'Investigate Incident'."
        )

        return

    confidence = investigation.get(
        "confidence",
        "unknown",
    )

    confidence_color = {
        "high": "green",
        "medium": "orange",
        "low": "red",
    }.get(confidence.lower(), "grey")

    st.subheader("Incident Summary")

    st.write(
        investigation.get(
            "incident_summary",
            "No incident summary was generated.",
        )
    )

    st.markdown(
        (
            f"**Confidence:** "
            f":{confidence_color}[{confidence.upper()}]"
        )
    )

    st.subheader("Confirmed Evidence")

    confirmed_evidence = investigation.get(
        "confirmed_evidence",
        [],
    )

    if confirmed_evidence:
        for evidence_item in confirmed_evidence:
            st.markdown(f"- {evidence_item}")
    else:
        st.info("No confirmed evidence was returned.")

    st.subheader("Likely Causes or Hypotheses")

    hypotheses = investigation.get(
        "likely_causes_or_hypotheses",
        [],
    )

    for hypothesis in hypotheses:
        st.markdown(f"- {hypothesis}")

    st.warning(
        "Hypotheses are not confirmed facts unless explicitly "
        "supported by a cited evidence record."
    )

    st.subheader("Affected Assets")

    affected_assets = investigation.get(
        "affected_assets",
        [],
    )

    for affected_asset in affected_assets:
        st.markdown(f"- {affected_asset}")

    st.subheader("Recommended Investigation")

    recommendations = investigation.get(
        "recommended_investigation",
        [],
    )

    for recommendation in recommendations:
        st.markdown(f"- {recommendation}")

    st.info(
        "These are recommended investigation steps. "
        "The assistant has not executed any remediation."
    )

    limitations = investigation.get(
        "limitations",
        [],
    )

    if limitations:
        st.subheader("Limitations")

        for limitation in limitations:
            st.markdown(f"- {limitation}")

    citations = investigation.get(
        "citations",
        [],
    )

    if citations:
        st.subheader("Evidence Citations")

        for citation in citations:
            st.code(citation)

    if evidence_bundle:
        with st.expander("View Raw Evidence Bundle"):
            st.json(evidence_bundle)
        st.divider()

    st.subheader("Ask About This Incident")

    st.caption(
        "Ask about the summary, cause, evidence, impact, "
        "quality tests, Airflow logs, status or recommended "
        "investigation."
    )

    question = st.text_input(
        "Your question",
        placeholder=(
            "For example: What evidence confirms this incident?"
        ),
        key=f"incident_question_{selected_incident_id}",
    )

    answer_mode = st.radio(
        "Answer mode",
        options=["rules", "llm"],
        format_func=lambda mode: (
            "Rule-based (baseline)" if mode == "rules" else "LLM + runbooks"
        ),
        horizontal=True,
        key=f"answer_mode_{selected_incident_id}",
    )

    ask_button = st.button(
        "Ask Assistant",
        type="primary",
        use_container_width=True,
        disabled=not question.strip(),
    )

    if ask_button:
        with st.spinner(
            "Searching the permitted incident evidence..."
        ):
            try:
                question_response = post_assistant_api(
                    (
                        f"/api/v1/incidents/"
                        f"{selected_incident_id}/questions"
                        f"?mode={answer_mode}"
                    ),
                    {
                        "question": question.strip(),
                    },
                )

            except RuntimeError as error:
                st.error(str(error))
                return

        st.session_state["question_response"] = (
            question_response
        )

        st.session_state["question_incident_id"] = (
            selected_incident_id
        )

    question_response = st.session_state.get(
        "question_response"
    )

    question_incident_id = st.session_state.get(
        "question_incident_id"
    )

    if (
        question_response
        and question_incident_id == selected_incident_id
    ):
        st.subheader("Assistant Answer")

        if question_response.get("refused"):
            st.warning(
                question_response.get(
                    "answer",
                    "The question could not be answered.",
                )
            )

        else:
            st.success(
                question_response.get(
                    "answer",
                    "No answer was returned.",
                )
            )

        answer_column, confidence_column = st.columns(2)

        answer_column.metric(
            "Response Type",
            question_response.get(
                "response_type",
                "unknown",
            ),
        )

        confidence_column.metric(
            "Confidence",
            question_response.get(
                "confidence",
                "unknown",
            ).upper(),
        )

        answer_citations = question_response.get(
            "citations",
            [],
        )

        if answer_citations:
            st.markdown("**Answer citations**")

            for citation in answer_citations:
                st.code(citation)

        answer_limitations = question_response.get(
            "limitations",
            [],
        )

        if answer_limitations:
            with st.expander("Answer limitations"):
                for limitation in answer_limitations:
                    st.markdown(f"- {limitation}")
                    
st.title("🔭 AI-Assisted Data Observability Platform")

st.caption(
    "Pipeline reliability, data-quality monitoring, "
    "incident investigation and lineage impact analysis"
)


with st.sidebar:
    st.header("Dashboard Navigation")

    selected_page = st.radio(
        "Select a page",
      [
    "Overview",
    "Pipeline Runs",
    "Data Quality",
    "Incidents",
    "Lineage",
    "Assistant",
        ]   ,
    )

    st.divider()

    if st.button("Refresh Dashboard", use_container_width=True):
        clear_query_cache()
        st.rerun()


try:
    database_connected = test_connection()
except Exception as error:
    database_connected = False
    st.error(f"Database connection failed: {error}")


if not database_connected:
    st.stop()


if selected_page == "Overview":
    show_overview()

elif selected_page == "Pipeline Runs":
    show_pipeline_runs()

elif selected_page == "Data Quality":
    show_data_quality()

elif selected_page == "Incidents":
    show_incidents()

elif selected_page == "Lineage":
    show_lineage()

elif selected_page == "Assistant":
    show_assistant()    