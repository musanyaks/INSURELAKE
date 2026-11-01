"""Score each claims micro-batch with the fraud model; publish alerts upstream."""
import os
import pickle

import numpy as np
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, DoubleType, TimestampType, StructType, StructField

KAFKA        = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
ICEBERG_REST = os.getenv("ICEBERG_REST_URI", "http://iceberg-rest:8181")
WAREHOUSE    = os.getenv("ICEBERG_WAREHOUSE", "s3://warehouse/")
CHECKPOINTS  = os.getenv("CHECKPOINT_ROOT", "s3a://checkpoints/")
MODEL_PATH   = os.getenv("FRAUD_MODEL_PATH", "/opt/ml-models/fraud_xgb.pkl")
THRESHOLD    = float(os.getenv("FRAUD_THRESHOLD", "0.65"))

COUNTY_RISK = {
    "Nairobi": 0.8, "Mombasa": 0.8, "Kisumu": 0.75, "Nakuru": 0.7, "Kiambu": 0.7,
    "Machakos": 0.5, "Uasin Gishu": 0.5, "Kakamega": 0.5, "Meru": 0.5, "Kajiado": 0.5,
}


def build_spark() -> SparkSession:
    return (SparkSession.builder
        .appName("insurelake.fraud")
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.ice",          "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.ice.type",     "rest")
        .config("spark.sql.catalog.ice.uri",      ICEBERG_REST)
        .config("spark.sql.catalog.ice.warehouse", WAREHOUSE)
        .config("spark.sql.catalog.ice.io-impl",  "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.hadoop.fs.s3a.endpoint",    "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key",  "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key",  "minioadmin")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate())


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def build_features(pdf: pd.DataFrame) -> pd.DataFrame:
    pdf = pdf.copy()
    pdf["log_amount"]              = np.log1p(pdf["claim_amount"].astype(float))
    pdf["days_since_policy_start"] = 60  # joined against policy table in production
    pdf["customer_claim_count"]    = 0
    pdf["policy_claim_count"]      = 0
    pdf["provider_claim_count"]    = 0
    pdf["county_risk"]             = pdf["county"].map(COUNTY_RISK).fillna(0.3)
    pdf["is_weekend"]              = pd.to_datetime(pdf["claim_date"]).dt.dayofweek >= 5
    pdf["hour_of_day"]             = pd.Timestamp.utcnow().hour
    pdf["dup_score"]               = 0.0
    return pdf


def main():
    spark = build_spark()
    model = load_model()
    features = model.get_booster().feature_names

    def score_and_publish(batch_df, _batch_id):
        if batch_df.rdd.isEmpty():
            return
        pdf = build_features(batch_df.toPandas())

        pdf["fraud_score"] = model.predict_proba(
            pdf[features].fillna(0).astype(float))[:, 1]
        pdf["risk_level"] = np.select(
            [pdf.fraud_score >= 0.85, pdf.fraud_score >= THRESHOLD, pdf.fraud_score >= 0.4],
            ["CRITICAL", "HIGH", "MEDIUM"], default="LOW")
        pdf["model_version"] = os.getenv("MODEL_VERSION", "fraud_xgb_v1")
        pdf["scored_at"] = pd.Timestamp.utcnow().tz_localize(None)
        pdf["reasons"] = pdf.apply(_reasons, axis=1)

        scores_df = spark.createDataFrame(pdf[[
            "claim_id", "fraud_score", "risk_level",
            "reasons", "model_version", "scored_at"]])

        # 1. Persist scores (Iceberg append - dedupe via dbt downstream)
        (scores_df.writeTo("ice.silver.fraud_scores")
                   .using("iceberg").append())

        # 2. Publish alerts to Kafka
        alerts = pdf[pdf.fraud_score >= THRESHOLD][[
            "claim_id", "customer_id", "claim_amount",
            "county", "fraud_score", "risk_level", "reasons"]]
        if not alerts.empty:
            (spark.createDataFrame(alerts)
                .selectExpr("to_json(struct(*)) AS value")
                .write
                .format("kafka")
                .option("kafka.bootstrap.servers", KAFKA)
                .option("topic", "insurance.fraud_alerts")
                .save())

    (spark.readStream.format("iceberg")
        .option("stream-from-timestamp", "0")
        .load("ice.silver.claims")
        .writeStream
        .foreachBatch(score_and_publish)
        .option("checkpointLocation", f"{CHECKPOINTS}fraud_scores/")
        .trigger(processingTime="15 seconds")
        .start()
        .awaitTermination())


def _reasons(row):
    reasons = []
    if row["county_risk"] >= 0.7:     reasons.append("High-risk county")
    if row["log_amount"] > 13:        reasons.append("Amount above historical average")
    if row["is_weekend"]:             reasons.append("Submitted on weekend")
    return " | ".join(reasons) if reasons else "No rule flags raised"


if __name__ == "__main__":
    main()