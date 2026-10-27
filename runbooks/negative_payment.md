# negative_payment

## Symptoms
A payment record arrives with an amount below zero. Revenue and payment
models undercount if the record reaches analytics.

## Where it is detected
Ingestion validation rejects the record and writes it to quarantine.
Severity: critical.

## Likely causes
- A refund or reversal sent as a payment instead of a separate refund event
- A sign error in the upstream payment export
- A test or manually injected record

## How to confirm
1. Find the record in the quarantine table for the batch date.
2. Check whether the same payment_id has a matching positive payment.
3. Check the source file for other negative amounts in the same batch.

## Fix
Correct or remove the record at the source and re-run the batch.
Never edit raw data in place.

## Prevention
Keep the non-negative amount check at ingestion and add a dbt test on the
payments model as a second layer.
