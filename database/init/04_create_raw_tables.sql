CREATE TABLE IF NOT EXISTS raw.customers (
    raw_record_id BIGSERIAL PRIMARY KEY,

    customer_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(250) NOT NULL,
    email VARCHAR(320) NOT NULL,
    country VARCHAR(100) NOT NULL,
    registration_date DATE NOT NULL,
    status VARCHAR(30) NOT NULL,

    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE,
    source_row_number BIGINT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL,

    CONSTRAINT fk_raw_customers_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_raw_customer_record
        UNIQUE (file_checksum, source_row_number)
);


CREATE TABLE IF NOT EXISTS raw.products (
    raw_record_id BIGSERIAL PRIMARY KEY,

    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(250) NOT NULL,
    category VARCHAR(100) NOT NULL,
    supplier_id VARCHAR(50) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    active BOOLEAN NOT NULL,

    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE,
    source_row_number BIGINT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL,

    CONSTRAINT fk_raw_products_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_raw_product_record
        UNIQUE (file_checksum, source_row_number)
);


CREATE TABLE IF NOT EXISTS raw.orders (
    raw_record_id BIGSERIAL PRIMARY KEY,

    order_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    order_date TIMESTAMP NOT NULL,
    status VARCHAR(30) NOT NULL,
    currency CHAR(3) NOT NULL,
    order_total NUMERIC(14, 2) NOT NULL,

    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE NOT NULL,
    source_row_number BIGINT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL,

    CONSTRAINT fk_raw_orders_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_raw_order_record
        UNIQUE (file_checksum, source_row_number)
);


CREATE TABLE IF NOT EXISTS raw.order_items (
    raw_record_id BIGSERIAL PRIMARY KEY,

    item_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    discount NUMERIC(5, 4) NOT NULL,
    line_total NUMERIC(14, 2) NOT NULL,

    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE NOT NULL,
    source_row_number BIGINT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL,

    CONSTRAINT fk_raw_order_items_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_raw_order_item_record
        UNIQUE (file_checksum, source_row_number)
);


CREATE TABLE IF NOT EXISTS raw.payments (
    raw_record_id BIGSERIAL PRIMARY KEY,

    payment_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    status VARCHAR(30) NOT NULL,
    method VARCHAR(50) NOT NULL,

    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE NOT NULL,
    source_row_number BIGINT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL,

    CONSTRAINT fk_raw_payments_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_raw_payment_record
        UNIQUE (file_checksum, source_row_number)
);


CREATE TABLE IF NOT EXISTS raw.shipments (
    raw_record_id BIGSERIAL PRIMARY KEY,

    shipment_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    expected_delivery_date DATE NOT NULL,
    actual_delivery_date DATE,
    status VARCHAR(30) NOT NULL,
    warehouse_id VARCHAR(50) NOT NULL,

    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE NOT NULL,
    source_row_number BIGINT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL,

    CONSTRAINT fk_raw_shipments_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_raw_shipment_record
        UNIQUE (file_checksum, source_row_number)
);


CREATE TABLE IF NOT EXISTS raw.inventory (
    raw_record_id BIGSERIAL PRIMARY KEY,

    inventory_date DATE NOT NULL,
    warehouse_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    stock_quantity INTEGER NOT NULL,
    reorder_level INTEGER NOT NULL,

    source_file VARCHAR(500) NOT NULL,
    file_checksum CHAR(64) NOT NULL,
    batch_date DATE NOT NULL,
    source_row_number BIGINT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL,

    CONSTRAINT fk_raw_inventory_run
        FOREIGN KEY (run_id)
        REFERENCES observability.pipeline_runs(run_id),

    CONSTRAINT uq_raw_inventory_record
        UNIQUE (file_checksum, source_row_number)
);


CREATE INDEX IF NOT EXISTS idx_raw_customers_customer_id
    ON raw.customers(customer_id);

CREATE INDEX IF NOT EXISTS idx_raw_products_product_id
    ON raw.products(product_id);

CREATE INDEX IF NOT EXISTS idx_raw_orders_order_id
    ON raw.orders(order_id);

CREATE INDEX IF NOT EXISTS idx_raw_orders_customer_id
    ON raw.orders(customer_id);

CREATE INDEX IF NOT EXISTS idx_raw_orders_batch_date
    ON raw.orders(batch_date);

CREATE INDEX IF NOT EXISTS idx_raw_order_items_order_id
    ON raw.order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_raw_order_items_product_id
    ON raw.order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_raw_payments_order_id
    ON raw.payments(order_id);

CREATE INDEX IF NOT EXISTS idx_raw_shipments_order_id
    ON raw.shipments(order_id);

CREATE INDEX IF NOT EXISTS idx_raw_inventory_product_id
    ON raw.inventory(product_id);

CREATE INDEX IF NOT EXISTS idx_raw_inventory_date
    ON raw.inventory(inventory_date);