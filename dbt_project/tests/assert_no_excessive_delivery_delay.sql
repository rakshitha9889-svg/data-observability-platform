select
    shipment_id,
    order_id,
    expected_delivery_date,
    actual_delivery_date,
    delivery_delay_days

from {{ ref('fact_shipments') }}

where delivery_delay_days > 7