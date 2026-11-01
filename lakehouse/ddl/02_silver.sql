CREATE TABLE IF NOT EXISTS ice.silver.claims (
    claim_id      STRING,
    policy_id     STRING,
    customer_id   STRING,
    claim_type    STRING,
    claim_amount  DECIMAL(18,2),
    claim_date    DATE,
    county        STRING,
    provider_id   STRING,
    vehicle_id    STRING,
    status        STRING,
    description   STRING,
    fraud_score   DOUBLE,
    ingested_at   TIMESTAMP,
    updated_at    TIMESTAMP
)
USING iceberg
PARTITIONED BY (months(claim_date))
TBLPROPERTIES (
    'format-version'                = '2',
    'write.merge.mode'              = 'copy-on-write',
    'write.delete.mode'             = 'copy-on-write',
    'write.update.mode'             = 'copy-on-write'
);

CREATE TABLE IF NOT EXISTS ice.silver.payments (
    payment_id   STRING,
    claim_id     STRING,
    amount       DECIMAL(18,2),
    method       STRING,
    mpesa_receipt STRING,
    payment_date DATE,
    status       STRING,
    updated_at   TIMESTAMP
)
USING iceberg
PARTITIONED BY (months(payment_date));

CREATE TABLE IF NOT EXISTS ice.silver.fraud_scores (
    claim_id     STRING,
    fraud_score  DOUBLE,
    risk_level   STRING,
    reasons      STRING,
    model_version STRING,
    scored_at    TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(scored_at));