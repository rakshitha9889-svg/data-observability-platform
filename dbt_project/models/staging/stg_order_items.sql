with ranked_items as (

    select
        item_id,
        order_id,
        product_id,
        quantity::integer as quantity,
        unit_price::numeric(12, 2) as unit_price,
        discount::numeric(5, 4) as discount,
        line_total::numeric(14, 2) as line_total,
        batch_date,
        source_file,
        file_checksum,
        record_hash,
        ingested_at,
        run_id,

        row_number() over (
            partition by item_id
            order by ingested_at desc, raw_record_id desc
        ) as record_rank

    from {{ source('raw', 'order_items') }}

)

select
    item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount,
    line_total,
    batch_date,
    source_file,
    file_checksum,
    record_hash,
    ingested_at,
    run_id

from ranked_items

where record_rank = 1