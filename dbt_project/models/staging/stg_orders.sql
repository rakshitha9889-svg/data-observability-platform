with ranked_orders as (

    select
        order_id,
        customer_id,
        order_date,
        lower(trim(status)) as order_status,
        upper(trim(currency)) as currency,
        order_total::numeric(14, 2) as order_total,
        batch_date,
        source_file,
        file_checksum,
        record_hash,
        ingested_at,
        run_id,

        row_number() over (
            partition by order_id
            order by ingested_at desc, raw_record_id desc
        ) as record_rank

    from {{ source('raw', 'orders') }}

)

select
    order_id,
    customer_id,
    order_date,
    order_status,
    currency,
    order_total,
    batch_date,
    source_file,
    file_checksum,
    record_hash,
    ingested_at,
    run_id

from ranked_orders

where record_rank = 1