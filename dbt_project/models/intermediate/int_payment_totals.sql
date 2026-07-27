select
    order_id,
    count(*) as payment_attempt_count,

    round(
        sum(
            case
                when payment_status = 'successful'
                then payment_amount
                else 0
            end
        ),
        2
    ) as successful_payment_total,

    max(
        case
            when payment_status = 'successful'
            then 1
            else 0
        end
    )::boolean as has_successful_payment

from {{ ref('stg_payments') }}

group by order_id