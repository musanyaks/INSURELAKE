"""Build claims_development.parquet and fact_claims.parquet from data/raw/claims.csv."""
import numpy as np
import pandas as pd

PATTERN = np.array([0.30, 0.20, 0.15, 0.10, 0.08, 0.06, 0.04, 0.03, 0.02, 0.01, 0.005, 0.005])


def main() -> None:
    claims = pd.read_csv("data/raw/claims.csv", parse_dates=["claim_date"])
    now = (pd.Timestamp.today().normalize() - pd.Timedelta(days=1)).to_period("M")

    # The script masks a 12 x 12 triangle, so keep exactly the last 12 origin months.
    claims["origin"] = claims["claim_date"].dt.to_period("M")
    claims = claims[(claims["origin"] > now - 12) & (claims["origin"] <= now)].copy()
    claims["age"] = (now - claims["origin"]).apply(lambda x: x.n)  # max observable dev month

    paid = claims[claims["status"].isin(["Paid", "Approved"])]
    rows = []
    for dev_month, weight in enumerate(PATTERN):
        sub = paid[paid["age"] >= dev_month]
        rows.append(pd.DataFrame({
            "claim_id": sub["claim_id"],
            "claim_date": sub["claim_date"],
            "dev_month": dev_month,
            "paid_amount": (sub["claim_amount"] * weight).round(2),
        }))
    dev = pd.concat(rows, ignore_index=True)

    dev.to_parquet("claims_development.parquet", index=False)
    claims["premium"] = (claims["claim_amount"] / 0.65).round(2)
    claims.drop(columns=["origin", "age"]).to_parquet("fact_claims.parquet", index=False)
    print(f"saved -> claims_development.parquet ({len(dev)} rows), fact_claims.parquet ({len(claims)} rows)")


if __name__ == "__main__":
    main()