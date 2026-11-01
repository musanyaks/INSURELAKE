CREATE SCHEMA IF NOT EXISTS ice.bronze;
CREATE SCHEMA IF NOT EXISTS ice.silver;
CREATE SCHEMA IF NOT EXISTS ice.gold;
CREATE SCHEMA IF NOT EXISTS ice.governance;CREATE TABLE IF NOT EXISTS ice.bronze.claims (
    payload        STRING,
    kafka_topic    STRING,
    kafka_partition INT,
    kafka_offset   BIGINT,
    kafka_ts       TIMESTAMP,
    event_date     DATE
)
USING iceberg
PARTITIONED BY (days(event_date))
TBLPROPERTIES (
    'write.target-file-size-bytes'      = '134217728',
    'write.parquet.compression-codec'   = 'zstd',
    'format-version'                    = '2'
);

CREATE TABLE IF NOT EXISTS ice.bronze.mpesa (
    payload     STRING,
    kafka_ts    TIMESTAMP,
    event_date  DATE
)
USING iceberg
PARTITIONED BY (days(event_date));CREATE TABLE IF NOT EXISTS ice.silver.claims (
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
PARTITIONED BY (days(scored_at));CREATE TABLE IF NOT EXISTS ice.gold.fact_claims (
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