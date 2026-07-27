with ranked_payments as (

    select
        payment_id,
        order_id,
        payment_date,
        amount::numeric(14, 2) as payment_amount,
        lower(trim(status)) as payment_status,
        lower(trim(method)) as payment_method,
        batch_date,
        source_file,
        file_checksum,
        record_hash,
        ingested_at,
        run_id,

        row_number() over (
            partition by payment_id
            order by ingested_at desc, raw_record_id desc
        ) as record_rank

    from {{ source('raw', 'payments') }}

)

select
    payment_id,
    order_id,
    payment_date,
    payment_amount,
    payment_status,
    payment_method,
    batch_date,
    source_file,
    file_checksum,
    record_hash,
    ingested_at,
    run_id

from ranked_payments

where record_rank = 1