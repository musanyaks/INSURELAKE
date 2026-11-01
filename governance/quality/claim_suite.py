"""Great Expectations suite for silver.claims.

Runs daily via Airflow and publishes a pass/fail row to gold.governance.dq_runs
so the executive dashboard has a live data-quality score.
"""
import os

import duckdb
import os
os.environ.setdefault("USERPROFILE", r"C:\Users\HomePC")
import great_expectations as gx
import pandas as pd

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")


def load_silver_claims() -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_endpoint='{MINIO_ENDPOINT}';")
    con.execute("SET s3_access_key_id='minioadmin';")
    con.execute("SET s3_secret_access_key='minioadmin';")
    con.execute("SET s3_use_ssl=false;")
    con.execute("SET s3_url_style='path';")
    con.execute("SET s3_url_style='path';")
    con.execute("SET s3_url_style='path';")
    return con.execute("""
        SELECT * FROM read_parquet('s3://warehouse/silver/claims/**/*.parquet')
    """).df()


def main() -> dict:
    df = load_silver_claims()
    context = gx.get_context()

    ds    = context.sources.add_or_update_pandas("claims")
    asset = ds.add_dataframe_asset(name="silver_claims")
    batch = asset.build_batch_request(dataframe=df)

    suite_name = "silver_claims_suite"
    context.add_or_update_expectation_suite(suite_name)
    validator = context.get_validator(
        batch_request=batch, expectation_suite_name=suite_name)

    # --- core integrity ---
    validator.expect_column_values_to_not_be_null("claim_id")
    validator.expect_column_values_to_be_unique("claim_id")
    validator.expect_column_values_to_not_be_null("customer_id")
    validator.expect_column_values_to_not_be_null("policy_id")

    # --- validity ---
    validator.expect_column_values_to_be_between("claim_amount", 0, 1_000_000_000)
    validator.expect_column_values_to_be_in_set(
        "claim_type", ["Motor", "Health", "Life", "Property", "Microinsurance"])
    validator.expect_column_values_to_be_in_set(
        "status", ["Submitted", "Approved", "Paid", "Rejected"])

    # --- timeliness (no claim older than the ingestion window) ---
    validator.expect_column_values_to_be_between(
        "claim_date",
        min_value=str((pd.Timestamp.utcnow() - pd.Timedelta(days=730)).date()),
        max_value=str(pd.Timestamp.utcnow().date()))

    # --- volume sanity ---
    validator.expect_table_row_count_to_be_between(1, 100_000_000)

    result = validator.validate()
    stats  = result["statistics"]

    score = (stats["successful_expectations"] /
             max(stats["evaluated_expectations"], 1))

    run = pd.DataFrame([{
        "generated_at": pd.Timestamp.utcnow(),
        "success":      bool(result["success"]),
        "evaluated":    stats["evaluated_expectations"],
        "successful":   stats["successful_expectations"],
        "failed":       stats["unsuccessful_expectations"],
        "score":        round(score, 4),
        "suite":        suite_name,
    }])
    print(run.to_string(index=False))
    return run.iloc[0].to_dict()


if __name__ == "__main__":
    print(main())