with ranked_shipments as (

    select
        shipment_id,
        order_id,
        expected_delivery_date,
        actual_delivery_date,
        lower(trim(status)) as shipment_status,
        warehouse_id,
        batch_date,
        source_file,
        file_checksum,
        record_hash,
        ingested_at,
        run_id,

        row_number() over (
            partition by shipment_id
            order by ingested_at desc, raw_record_id desc
        ) as record_rank

    from {{ source('raw', 'shipments') }}

)

select
    shipment_id,
    order_id,
    expected_delivery_date,
    actual_delivery_date,
    shipment_status,
    warehouse_id,
    batch_date,
    source_file,
    file_checksum,
    record_hash,
    ingested_at,
    run_id

from ranked_shipments

where record_rank = 1