select
    inventory_date,
    warehouse_id,
    product_id,
    stock_quantity,
    reorder_level,

    case
        when stock_quantity = 0 then 'stockout'
        when stock_quantity <= reorder_level then 'low_stock'
        else 'healthy'
    end as inventory_status,

    stock_quantity = 0 as is_stockout,

    stock_quantity <= reorder_level
        as requires_reorder

from {{ ref('stg_inventory') }}