select
    payment_id,
    order_id,
    payment_date,
    payment_date::date as payment_date_key,
    payment_amount,
    payment_status,
    payment_method,
    payment_status = 'successful' as is_successful,
    batch_date,
    run_id

from {{ ref('stg_payments') }}