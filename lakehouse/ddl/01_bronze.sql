CREATE TABLE IF NOT EXISTS ice.bronze.claims (
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
PARTITIONED BY (days(event_date));