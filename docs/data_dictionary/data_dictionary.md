# Data Dictionary

## Customers

| Column | Type | Nullable | Unique | Description | Sensitivity |
|---|---|---:|---:|---|---|
| customer_id | string | No | Yes | Customer identifier | Internal |
| customer_name | string | No | No | Synthetic customer name | Synthetic PII |
| email | string | No | Yes | Synthetic email address | Synthetic PII |
| country | string | No | No | Customer country | Internal |
| registration_date | date | No | No | Registration date | Internal |
| status | string | No | No | active, inactive or suspended | Internal |

## Products

| Column | Type | Nullable | Unique | Description | Sensitivity |
|---|---|---:|---:|---|---|
| product_id | string | No | Yes | Product identifier | Internal |
| product_name | string | No | No | Product name | Public |
| category | string | No | No | Product category | Public |
| supplier_id | string | No | No | Supplier identifier | Internal |
| unit_price | decimal | No | No | Standard unit price | Internal |
| active | boolean | No | No | Product availability flag | Public |

## Orders

| Column | Type | Nullable | Unique | Description |
|---|---|---:|---:|---|
| order_id | string | No | Yes | Order identifier |
| customer_id | string | No | No | Customer identifier |
| order_date | datetime | No | No | Order creation time |
| status | string | No | No | completed, shipped, cancelled or processing |
| currency | string | No | No | Transaction currency |
| order_total | decimal | No | No | Total after item-level discounts |

## Order items

| Column | Type | Nullable | Unique | Description |
|---|---|---:|---:|---|
| item_id | string | No | Yes | Order-item identifier |
| order_id | string | No | No | Parent order |
| product_id | string | No | No | Purchased product |
| quantity | integer | No | No | Purchased units |
| unit_price | decimal | No | No | Price per unit |
| discount | decimal | No | No | Discount rate from 0 to 1 |
| line_total | decimal | No | No | Calculated item total |

## Payments

| Column | Type | Nullable | Unique | Description |
|---|---|---:|---:|---|
| payment_id | string | No | Yes | Payment identifier |
| order_id | string | No | No | Associated order |
| payment_date | datetime | No | No | Payment attempt time |
| amount | decimal | No | No | Payment amount |
| status | string | No | No | successful, failed, pending or refunded |
| method | string | No | No | Payment method |

## Shipments

| Column | Type | Nullable | Unique | Description |
|---|---|---:|---:|---|
| shipment_id | string | No | Yes | Shipment identifier |
| order_id | string | No | No | Associated order |
| expected_delivery_date | date | No | No | Promised delivery date |
| actual_delivery_date | date | Yes | No | Actual delivery date |
| status | string | No | No | delivered, in_transit, delayed or cancelled |
| warehouse_id | string | No | No | Origin warehouse |

## Inventory

| Column | Type | Nullable | Unique | Description |
|---|---|---:|---:|---|
| inventory_date | date | No | Composite | Inventory snapshot date |
| warehouse_id | string | No | Composite | Warehouse identifier |
| product_id | string | No | Composite | Product identifier |
| stock_quantity | integer | No | No | Available stock |
| reorder_level | integer | No | No | Replenishment threshold |