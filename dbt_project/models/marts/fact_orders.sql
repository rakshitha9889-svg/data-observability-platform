select
    orders.order_id,
    orders.customer_id,
    orders.order_date,
    orders.order_date::date as order_date_key,
    orders.order_status,
    orders.currency,
    orders.order_total,

    coalesce(
        items.item_line_count,
        0
    ) as item_line_count,

    coalesce(
        items.total_quantity,
        0
    ) as total_quantity,

    coalesce(
        items.calculated_item_total,
        0
    ) as calculated_item_total,

    round(
        orders.order_total
        - coalesce(items.calculated_item_total, 0),
        2
    ) as order_total_difference,

    coalesce(
        payments.successful_payment_total,
        0
    ) as successful_payment_total,

    coalesce(
        payments.has_successful_payment,
        false
    ) as has_successful_payment,

    orders.batch_date,
    orders.run_id

from {{ ref('stg_orders') }} as orders

left join {{ ref('int_order_item_totals') }} as items
    on orders.order_id = items.order_id

left join {{ ref('int_payment_totals') }} as payments
    on orders.order_id = payments.order_id