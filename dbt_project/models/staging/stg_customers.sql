with ranked_customers as (

    select
        customer_id,
        trim(customer_name) as customer_name,
        lower(trim(email)) as email,
        trim(country) as country,
        registration_date,
        lower(trim(status)) as customer_status,
        source_file,
        file_checksum,
        record_hash,
        ingested_at,
        run_id,

        row_number() over (
            partition by customer_id
            order by ingested_at desc, raw_record_id desc
        ) as record_rank

    from {{ source('raw', 'customers') }}

)

select
    customer_id,
    customer_name,
    email,
    country,
    registration_date,
    customer_status,
    source_file,
    file_checksum,
    record_hash,
    ingested_at,
    run_id

from ranked_customers

where record_rank = 1