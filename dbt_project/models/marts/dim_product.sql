select
    product_id,
    product_name,
    category,
    supplier_id,
    unit_price,
    active

from {{ ref('stg_products') }}