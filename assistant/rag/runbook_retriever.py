from typing import Any

from sqlalchemy import text

from assistant.config import get_database_engine
from assistant.models import EvidenceRecord
from assistant.rag.embedder import embed, to_pgvector

SEARCH_RUNBOOKS = text(
    "SELECT chunk_id, scenario, heading, content, "
    "1 - (embedding <=> CAST(:query AS vector)) AS similarity "
    "FROM observability.runbook_chunks "
    "ORDER BY embedding <=> CAST(:query AS vector) "
    "LIMIT :limit"
)


def to_evidence(row: dict[str, Any]) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=f"runbook:{row['chunk_id']}",
        source_table="observability.runbook_chunks",
        record={
            **row,
            "similarity": round(float(row["similarity"]), 3),
        },
    )


def search_runbooks(query: str, limit: int = 3) -> list[EvidenceRecord]:
    query_vector = to_pgvector(embed([query])[0])

    with get_database_engine().connect() as connection:
        rows = (
            connection.execute(
                SEARCH_RUNBOOKS,
                {"query": query_vector, "limit": limit},
            )
            .mappings()
            .all()
        )

    return [to_evidence(dict(row)) for row in rows]
