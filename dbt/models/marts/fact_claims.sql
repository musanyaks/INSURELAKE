{{ config(
    materialized='incremental',
    unique_key='claim_id',
    incremental_strategy='merge',
    partition_by='month(claim_date)',
) }}
SELECT
    {{ dbt_utils.generate_surrogate_key(['claim_id']) }} AS claim_sk,
    c.claim_id,
    c.policy_id,
    c.customer_id,
    CAST(c.claim_amount AS DECIMAL(18,2)) AS claim_amount,
    CAST(COALESCE(c.paid_amount, c.approved_amount, 0) AS DECIMAL(18,2)) AS paid_amount,
    c.claim_date,
    c.claim_type,
    c.county,
    c.status,
    COALESCE(c.fraud_score, 0) AS fraud_score,
    c.updated_at
FROM {{ ref('stg_claims') }} c
{% if is_incremental() %}
WHERE c.updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}