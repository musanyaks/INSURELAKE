import json
import pandas as pd
from pipeline._storage import read_parquet, write_parquet, mode


def _read_bronze(table):
    df = read_parquet(f"bronze/{table}")
    if df is None or df.empty:
        return pd.DataFrame()
    if "raw" in df.columns:
        parsed = pd.DataFrame([json.loads(r) for r in df["raw"]])
        if "ingested_at" in df.columns:
            parsed["_ingested_at"] = df["ingested_at"].values
        return parsed
    return df


def _dedup(df, key):
    if df.empty or key not in df.columns:
        return df
    if "_ingested_at" in df.columns:
        return df.sort_values("_ingested_at").drop_duplicates(subset=key, keep="last")
    return df.drop_duplicates(subset=key, keep="last")


def _clean_claims(df):
    if df.empty: return df
    df = _dedup(df, "claim_id")
    df["claim_amount"] = pd.to_numeric(df["claim_amount"], errors="coerce")
    if "paid_amount" in df.columns:
        df["paid_amount"] = pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0)
    df["claim_date"] = pd.to_datetime(df["claim_date"], errors="coerce")
    df = df.dropna(subset=["claim_id", "customer_id", "policy_id", "claim_amount", "claim_date"])
    return df[df["claim_amount"] > 0]


def _clean_payments(df):
    if df.empty: return df
    df = _dedup(df, "payment_id")
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df[df["amount"] > 0]
    return df


def main():
    print(f"[bronze->silver] storage: {mode()}")
    customers = _dedup(_read_bronze("customers"), "customer_id")
    policies  = _dedup(_read_bronze("policies"),  "policy_id")
    claims    = _clean_claims(_read_bronze("claims"))
    payments  = _clean_payments(_read_bronze("payments"))
    providers = _dedup(_read_bronze("providers"), "provider_id")

    if not policies.empty and not claims.empty:
        claims = claims[claims["policy_id"].isin(policies["policy_id"])]
    if not customers.empty and not claims.empty:
        claims = claims[claims["customer_id"].isin(customers["customer_id"])]

    for df in [customers, policies, claims, payments, providers]:
        if not df.empty:
            df.drop(columns=[c for c in df.columns if c.startswith("_")], inplace=True, errors="ignore")

    write_parquet(customers, "silver/customer/part-0.parquet")
    write_parquet(policies,  "silver/policy/part-0.parquet")
    write_parquet(claims,    "silver/claim/part-0.parquet")
    write_parquet(payments,  "silver/payment/part-0.parquet")
    write_parquet(providers, "silver/provider/part-0.parquet")
    print(f"[bronze->silver] done")


if __name__ == "__main__":
    main()
