"""Bronze -> Silver claim ingestion with exactly-once Iceberg sinks."""
import os

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
)

KAFKA          = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
ICEBERG_REST   = os.getenv("ICEBERG_REST_URI", "http://iceberg-rest:8181")
WAREHOUSE      = os.getenv("ICEBERG_WAREHOUSE", "s3://warehouse/")
CHECKPOINTS    = os.getenv("CHECKPOINT_ROOT", "s3a://checkpoints/")
TOPIC          = "insurance.claims"


def build_spark() -> SparkSession:
    return (SparkSession.builder
        .appName("insurelake.claims")
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.ice",          "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.ice.type",     "rest")
        .config("spark.sql.catalog.ice.uri",      ICEBERG_REST)
        .config("spark.sql.catalog.ice.warehouse", WAREHOUSE)
        .config("spark.sql.catalog.ice.io-impl",  "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.hadoop.fs.s3a.endpoint",         "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key",       "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key",       "minioadmin")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate())


CLAIM_SCHEMA = StructType([
    StructField("claim_id",      StringType()),
    StructField("policy_id",     StringType()),
    StructField("customer_id",   StringType()),
    StructField("claim_type",    StringType()),
    StructField("claim_amount",  DoubleType()),
    StructField("claim_date",    StringType()),
    StructField("county",        StringType()),
    StructField("provider_id",   StringType()),
    StructField("vehicle_id",    StringType()),
    StructField("description",   StringType()),
    StructField("status",        StringType()),
    StructField("ingested_at",   StringType()),
])


def main():
    spark = build_spark()

    raw = (spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "earliest")
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", 5000)
        .load())

    # ---------- Bronze: raw event, append-only, preserving history ----------
    bronze_q = (raw
        .selectExpr(
            "CAST(value AS STRING) AS payload",
            "topic AS kafka_topic",
            "partition AS kafka_partition",
            "offset AS kafka_offset",
            "timestamp AS kafka_ts",
        )
        .withColumn("event_date", F.to_date("kafka_ts"))
        .writeStream
        .format("iceberg")
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINTS}bronze_claims/")
        .trigger(processingTime="10 seconds")
        .toTable("ice.bronze.claims"))

    # ---------- Silver: parse + MERGE (idempotent, handles replays) ----------
    parsed = (raw
        .select(F.from_json(F.col("value").cast("string"), CLAIM_SCHEMA).alias("e"))
        .select("e.*")
        .withColumn("claim_date",  F.to_date("claim_date", "yyyy-MM-dd"))
        .withColumn("ingested_at", F.to_timestamp("ingested_at"))
        .withColumn("updated_at",  F.current_timestamp()))

    def upsert(batch_df, _batch_id):
        if batch_df.rdd.isEmpty():
            return
        batch_df.createOrReplaceTempView("_micro_claims")
        spark.sql("""
            MERGE INTO ice.silver.claims AS t
            USING _micro_claims AS s
            ON  t.claim_id = s.claim_id
            WHEN MATCHED    AND s.updated_at > t.updated_at THEN UPDATE SET *
            WHEN NOT MATCHED                                  THEN INSERT *
        """)

    silver_q = (parsed.writeStream
        .foreachBatch(upsert)
        .option("checkpointLocation", f"{CHECKPOINTS}silver_claims/")
        .trigger(processingTime="10 seconds")
        .start())

    bronze_q.awaitTermination()
    silver_q.awaitTermination()


if __name__ == "__main__":
    main()