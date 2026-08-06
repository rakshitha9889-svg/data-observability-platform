from typing import Any

from sqlalchemy import text

from assistant.config import get_database_engine


def fetch_all(
    query: str,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    engine = get_database_engine()

    with engine.connect() as connection:
        result = connection.execute(
            text(query),
            parameters or {},
        )

        return [dict(row) for row in result.mappings().all()]


def fetch_one(
    query: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    rows = fetch_all(query, parameters)

    if not rows:
        return None

    return rows[0]
