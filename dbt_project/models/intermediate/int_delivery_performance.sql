select
    shipment_id,
    order_id,
    warehouse_id,
    expected_delivery_date,
    actual_delivery_date,
    shipment_status,

    case
        when actual_delivery_date is null then null
        else actual_delivery_date - expected_delivery_date
    end as delivery_delay_days,

    case
        when actual_delivery_date is null then null
        when actual_delivery_date <= expected_delivery_date then true
        else false
    end as delivered_on_time

from {{ ref('stg_shipments') }}