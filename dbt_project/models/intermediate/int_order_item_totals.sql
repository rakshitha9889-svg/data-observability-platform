select
    order_id,
    count(*) as item_line_count,
    sum(quantity) as total_quantity,
    round(sum(line_total), 2) as calculated_item_total

from {{ ref('stg_order_items') }}

group by order_id