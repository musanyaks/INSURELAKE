"""Generate fake Kenya insurance data into data/raw/*.csv."""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("data/raw")
COUNTIES = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Kisii", "Eldoret", "Nyeri"]
TYPES = ["Motor", "Health", "Life", "Property", "Microinsurance"]
STATUSES = ["Submitted", "Approved", "Paid", "Rejected"]


def main(n_customers: int = 2000, n_claims: int = 10000, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    OUT.mkdir(parents=True, exist_ok=True)
    today = pd.Timestamp.today().normalize()

    customers = pd.DataFrame({
        "customer_id": [f"CUS-{i:06d}" for i in range(1, n_customers + 1)],
        "county": rng.choice(COUNTIES, n_customers),
    })
    policies = pd.DataFrame({
        "policy_id": [f"POL-{i:05d}-0" for i in range(1, n_customers + 1)],
        "customer_id": customers["customer_id"],
        "claim_type": rng.choice(TYPES, n_customers),
        "start_date": today - pd.to_timedelta(rng.integers(400, 1400, n_customers), unit="D"),
    })
    idx = rng.integers(0, n_customers, n_claims)
    claims = pd.DataFrame({
        "claim_id": [f"CLM-{i:07d}" for i in range(1, n_claims + 1)],
        "policy_id": policies["policy_id"].values[idx],
        "customer_id": customers["customer_id"].values[idx],
        "claim_type": policies["claim_type"].values[idx],
        "claim_amount": rng.lognormal(11, 1.0, n_claims).round(2),
        "claim_date": (today - pd.to_timedelta(rng.integers(1, 700, n_claims), unit="D")).strftime("%Y-%m-%d"),
        "status": rng.choice(STATUSES, n_claims, p=[0.15, 0.30, 0.45, 0.10]),
        "county": customers["county"].values[idx],
        "provider_id": [f"PRV-{p:04d}" for p in rng.integers(1, 60, n_claims)],
        "vehicle_id": [f"VEH-{v:05d}" for v in rng.integers(1, 3000, n_claims)],
    })
    customers.to_csv(OUT / "customers.csv", index=False)
    policies.to_csv(OUT / "policies.csv", index=False)
    claims.to_csv(OUT / "claims.csv", index=False)
    print(f"saved -> {OUT}/ ({n_customers} customers, {n_claims} claims)")


if __name__ == "__main__":
    main()