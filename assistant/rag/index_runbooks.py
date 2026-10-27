"""Embed every runbook section and store it in observability.runbook_chunks.

Run after editing any file in runbooks/:

    python -m assistant.rag.index_runbooks
"""

from sqlalchemy import text

from assistant.config import get_database_engine
from assistant.rag.embedder import embed, to_pgvector
from assistant.rag.runbooks import RUNBOOK_DIRECTORY, load_runbook_chunks

INSERT_CHUNK = text(
    "INSERT INTO observability.runbook_chunks "
    "(scenario, source_file, heading, content, embedding) "
    "VALUES (:scenario, :source_file, :heading, :content, "
    "CAST(:embedding AS vector))"
)


def main() -> None:
    chunks = load_runbook_chunks()

    if not chunks:
        raise SystemExit(f"No runbook sections found in {RUNBOOK_DIRECTORY}")

    vectors = embed([chunk["content"] for chunk in chunks])

    with get_database_engine().begin() as connection:
        connection.execute(text("TRUNCATE observability.runbook_chunks"))

        for chunk, vector in zip(chunks, vectors, strict=True):
            connection.execute(
                INSERT_CHUNK,
                {**chunk, "embedding": to_pgvector(vector)},
            )

    scenarios = len({chunk["scenario"] for chunk in chunks})
    print(f"Indexed {len(chunks)} sections from {scenarios} runbooks.")


if __name__ == "__main__":
    main()
