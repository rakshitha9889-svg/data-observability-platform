select
    inventory_date,
    warehouse_id,
    product_id,
    stock_quantity,
    reorder_level,
    inventory_status,
    is_stockout,
    requires_reorder

from {{ ref('int_inventory_status') }}