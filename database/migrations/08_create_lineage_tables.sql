CREATE TABLE IF NOT EXISTS observability.lineage_assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    unique_name VARCHAR(500) NOT NULL UNIQUE,
    asset_type VARCHAR(50) NOT NULL,

    database_name VARCHAR(150),
    schema_name VARCHAR(150),
    object_name VARCHAR(250),

    owner_name VARCHAR(250),
    description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_lineage_asset_type
        CHECK (
            asset_type IN (
                'source',
                'model',
                'test',
                'kpi',
                'dashboard'
            )
        )
);


CREATE TABLE IF NOT EXISTS observability.lineage_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    upstream_asset_id UUID NOT NULL,
    downstream_asset_id UUID NOT NULL,

    edge_type VARCHAR(50) NOT NULL,
    source_system VARCHAR(50) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_lineage_upstream
        FOREIGN KEY (upstream_asset_id)
        REFERENCES observability.lineage_assets(asset_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_lineage_downstream
        FOREIGN KEY (downstream_asset_id)
        REFERENCES observability.lineage_assets(asset_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_lineage_edge
        UNIQUE (
            upstream_asset_id,
            downstream_asset_id,
            edge_type,
            source_system
        ),

    CONSTRAINT chk_no_self_lineage
        CHECK (
            upstream_asset_id <> downstream_asset_id
        )
);


CREATE TABLE IF NOT EXISTS observability.incident_impacted_assets (
    incident_id UUID NOT NULL,
    asset_id UUID NOT NULL,

    impact_depth INTEGER NOT NULL,
    impact_path TEXT NOT NULL,

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (incident_id, asset_id),

    CONSTRAINT fk_impact_incident
        FOREIGN KEY (incident_id)
        REFERENCES observability.incidents(incident_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_impact_asset
        FOREIGN KEY (asset_id)
        REFERENCES observability.lineage_assets(asset_id)
        ON DELETE CASCADE,

    CONSTRAINT chk_impact_depth
        CHECK (impact_depth >= 1)
);


CREATE INDEX IF NOT EXISTS idx_lineage_asset_type
    ON observability.lineage_assets(asset_type);

CREATE INDEX IF NOT EXISTS idx_lineage_asset_object
    ON observability.lineage_assets(object_name);

CREATE INDEX IF NOT EXISTS idx_lineage_edge_upstream
    ON observability.lineage_edges(upstream_asset_id);

CREATE INDEX IF NOT EXISTS idx_lineage_edge_downstream
    ON observability.lineage_edges(downstream_asset_id);

CREATE INDEX IF NOT EXISTS idx_impacted_asset_incident
    ON observability.incident_impacted_assets(incident_id);
    