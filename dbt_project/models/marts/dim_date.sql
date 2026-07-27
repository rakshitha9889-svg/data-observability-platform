with date_limits as (

    select
        min(order_date::date) as minimum_date,
        max(order_date::date) as maximum_date

    from {{ ref('stg_orders') }}

),

date_series as (

    select
        generate_series(
            minimum_date,
            maximum_date,
            interval '1 day'
        )::date as date_day

    from date_limits

)

select
    date_day,
    extract(year from date_day)::integer as year_number,
    extract(quarter from date_day)::integer as quarter_number,
    extract(month from date_day)::integer as month_number,
    trim(to_char(date_day, 'Month')) as month_name,
    extract(week from date_day)::integer as week_number,
    extract(day from date_day)::integer as day_of_month,
    extract(isodow from date_day)::integer as day_of_week,
    trim(to_char(date_day, 'Day')) as day_name,
    extract(isodow from date_day) in (6, 7) as is_weekend

from date_series