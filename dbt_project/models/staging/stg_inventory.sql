with ranked_inventory as (

    select
        inventory_date,
        warehouse_id,
        product_id,
        stock_quantity::integer as stock_quantity,
        reorder_level::integer as reorder_level,
        batch_date,
        source_file,
        file_checksum,
        record_hash,
        ingested_at,
        run_id,

        row_number() over (
            partition by
                inventory_date,
                warehouse_id,
                product_id
            order by ingested_at desc, raw_record_id desc
        ) as record_rank

    from {{ source('raw', 'inventory') }}

)

select
    inventory_date,
    warehouse_id,
    product_id,
    stock_quantity,
    reorder_level,
    batch_date,
    source_file,
    file_checksum,
    record_hash,
    ingested_at,
    run_id

from ranked_inventory

where record_rank = 1