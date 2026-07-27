select
    customer_id,
    customer_name,
    email,
    country,
    registration_date,
    customer_status

from {{ ref('stg_customers') }}