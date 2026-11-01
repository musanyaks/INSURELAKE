CREATE TABLE IF NOT EXISTS ice.gold.fact_claims (
    claim_sk       BIGINT,
    claim_id       STRING,
    policy_sk      BIGINT,
    customer_sk    BIGINT,
    provider_sk    BIGINT,
    claim_date     DATE,
    claim_type     STRING,
    county         STRING,
    claim_amount   DECIMAL(18,2),
    approved_amount DECIMAL(18,2),
    paid_amount    DECIMAL(18,2),
    premium        DECIMAL(18,2),
    status         STRING,
    fraud_score    DOUBLE,
    updated_at     TIMESTAMP
)
USING iceberg
PARTITIONED BY (months(claim_date));

CREATE TABLE IF NOT EXISTS ice.gold.dim_customer (
    customer_sk  STRING,
    customer_id  STRING,
    name         STRING,
    address      STRING,
    county       STRING,
    phone        STRING,
    version      INT,
    valid_from   TIMESTAMP,
    valid_to     TIMESTAMP,
    is_current   BOOLEAN
)
USING iceberg
PARTITIONED BY (bucket(16, customer_id));