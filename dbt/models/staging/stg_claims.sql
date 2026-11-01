{{ config(materialized='view') }}
SELECT
    claim_id,
    policy_id,
    customer_id,
    claim_type,
    claim_date,
    claim_amount,
    COALESCE(county, 'UNKNOWN') AS county,
    provider_id,
    status,
    fraud_score,
    updated_at
FROM {{ source('iceberg', 'claims') }}
WHERE claim_amount > 0