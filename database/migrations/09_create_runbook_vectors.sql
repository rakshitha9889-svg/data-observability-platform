-- Runbook chunks with embeddings for the LLM incident-triage mode.
-- Requires the pgvector extension (docker image pgvector/pgvector:pg16).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS observability.runbook_chunks (
    chunk_id SERIAL PRIMARY KEY,
    scenario VARCHAR(150) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    heading VARCHAR(255),
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE observability.runbook_chunks IS
    'Runbook sections embedded with all-MiniLM-L6-v2 for semantic retrieval.';
