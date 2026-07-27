select
    order_id,
    order_total

from {{ ref('fact_orders') }}

where order_total < 0