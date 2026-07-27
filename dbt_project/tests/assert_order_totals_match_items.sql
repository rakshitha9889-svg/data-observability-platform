select
    order_id,
    order_total,
    calculated_item_total,
    order_total_difference

from {{ ref('fact_orders') }}

where abs(order_total_difference) > 0.01