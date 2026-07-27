select
    shipment_id,
    order_id,
    warehouse_id,
    expected_delivery_date,
    actual_delivery_date,
    shipment_status,
    delivery_delay_days,
    delivered_on_time

from {{ ref('int_delivery_performance') }}