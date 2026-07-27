select
    shipment_id,
    expected_delivery_date,
    actual_delivery_date

from {{ ref('fact_shipments') }}

where actual_delivery_date is not null
  and actual_delivery_date
      < expected_delivery_date - interval '30 days'