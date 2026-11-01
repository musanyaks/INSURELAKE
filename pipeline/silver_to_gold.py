import numpy as np
import pandas as pd
from pipeline._storage import read_parquet, write_parquet, mode


def _or_empty(df):
    return df if df is not None else pd.DataFrame()


def main():
    print(f"[silver->gold] storage: {mode()}")
    claims    = _or_empty(read_parquet("silver/claim"))
    policies  = _or_empty(read_parquet("silver/policy"))
    customers = _or_empty(read_parquet("silver/customer"))
    payments  = _or_empty(read_parquet("silver/payment"))
    providers = _or_empty(read_parquet("silver/provider"))

    if claims.empty or policies.empty:
        print("[silver->gold] silver empty - run `make seed` (or seed_local) first")
        return

    keep_pol = [c for c in ["policy_id", "agent_id", "vehicle_id", "product_type", "premium"]
                if c in policies.columns]
    fact = claims.merge(policies[keep_pol].drop_duplicates("policy_id"),
                        on="policy_id", how="left", suffixes=("", "_pol"))

    for col in ["fraud_score", "approved_amount", "paid_amount", "premium"]:
        if col not in fact.columns: fact[col] = np.nan

    keep = [c for c in [
        "claim_id", "policy_id", "customer_id", "vehicle_id", "provider_id",
        "claim_date", "claim_type", "claim_amount", "approved_amount", "paid_amount",
        "status", "county", "agent_id", "premium", "development_month", "fraud_score",
    ] if c in fact.columns]
    fact = fact[keep].copy()
    fact["claim_date"] = pd.to_datetime(fact["claim_date"])
    write_parquet(fact, "gold/fact_claims/part-0.parquet")

    if not customers.empty:
        d = customers.copy()
        d["valid_from"]  = pd.to_datetime(d.get("created_at"), errors="coerce").fillna(pd.Timestamp("2023-01-01"))
        d["valid_to"]    = pd.Timestamp("9999-12-31")
        d["is_current"]  = True
        d["version"]     = 1
        d["customer_sk"] = d["customer_id"] + "_v1"
        write_parquet(d, "gold/dim_customer/part-0.parquet")
    if not policies.empty:  write_parquet(policies,  "gold/dim_policy/part-0.parquet")
    if not providers.empty: write_parquet(providers, "gold/dim_provider/part-0.parquet")

    if "county" in fact.columns:
        dim_c = pd.DataFrame({"county": sorted(fact["county"].dropna().unique())})
        write_parquet(dim_c, "gold/dim_county/part-0.parquet")

    if "county" in fact.columns:
        ck = (fact.groupby("county")
                    .agg(total_claims       =("claim_id", "count"),
                         total_claim_amount =("claim_amount", "sum"),
                         total_paid         =("paid_amount", "sum"),
                         total_premium      =("premium", "sum"))
                    .reset_index())
        ck["loss_ratio"] = ck["total_paid"] / ck["total_premium"].replace(0, np.nan)
        write_parquet(ck, "gold/county_kpi/part-0.parquet")

    if "development_month" in fact.columns:
        tri = (fact[["claim_id", "claim_date", "development_month", "paid_amount", "claim_amount"]]
               .copy().rename(columns={"development_month": "dev_month"}))
        write_parquet(tri, "gold/claims_development/part-0.parquet")

    if not payments.empty:
        write_parquet(payments, "gold/fact_payments/part-0.parquet")
    print(f"[silver->gold] done (fact_claims={len(fact)})")


if __name__ == "__main__":
    main()
