with ranked_products as (

    select
        product_id,
        trim(product_name) as product_name,
        trim(category) as category,
        supplier_id,
        unit_price::numeric(12, 2) as unit_price,
        active,
        source_file,
        file_checksum,
        record_hash,
        ingested_at,
        run_id,

        row_number() over (
            partition by product_id
            order by ingested_at desc, raw_record_id desc
        ) as record_rank

    from {{ source('raw', 'products') }}

)

select
    product_id,
    product_name,
    category,
    supplier_id,
    unit_price,
    active,
    source_file,
    file_checksum,
    record_hash,
    ingested_at,
    run_id

from ranked_products

where record_rank = 1