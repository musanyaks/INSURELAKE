"""Local-only seed - writes ./data/silver/ without MinIO or Docker.
Run: python -m data_generator.seed_local
"""
import random
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np, pandas as pd

random.seed(7); np.random.seed(7)

COUNTIES = ["Nairobi","Mombasa","Kisumu","Nakuru","Kiambu","Machakos",
            "Uasin Gishu","Kakamega","Meru","Kajiado","Kisii","Nyeri"]
PROVIDERS = [f"PRV-{i:04d}" for i in range(1, 41)]
AGENTS    = [f"AGT-{i:04d}" for i in range(1, 26)]
TYPES     = ["Motor","Health","Life","Property","Microinsurance"]
BASE      = {"Motor":80_000,"Health":150_000,"Life":500_000,"Property":300_000,"Microinsurance":15_000}


def write(df, path):
    p = Path("data") / path; p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False); print(f"[seed-local] {len(df):>5} -> {p}")


def main():
    cust = pd.DataFrame([dict(
        customer_id=f"CUS-{i:06d}", name=f"Customer {i}",
        gender=random.choice(["M","F"]), age=random.randint(18,75),
        county=random.choice(COUNTIES),
        address=f"Building {random.randint(1,500)}, {random.choice(COUNTIES)}",
        phone=f"+2547{random.randint(10_000_000, 99_999_999)}",
        created_at=(datetime(2023,1,1)+timedelta(days=random.randint(0,900))).date().isoformat(),
    ) for i in range(1, 501)])

    pol_rows = []
    for i, c in cust.iterrows():
        for j in range(random.choices([1,1,2,3])[0]):
            start = datetime(2023,1,1)+timedelta(days=random.randint(0,700))
            pol_rows.append(dict(
                policy_id=f"POL-{i:05d}-{j}", customer_id=c["customer_id"],
                product_type=random.choice(TYPES),
                vehicle_id=f"VEH-{random.randint(1,5000):05d}",
                agent_id=random.choice(AGENTS),
                start_date=start.date().isoformat(),
                end_date=(start+timedelta(days=365)).date().isoformat(),
                premium=round(random.uniform(8_000,120_000),2),
                status=random.choices(["Active","Lapsed","Renewed"],weights=[0.7,0.15,0.15])[0],
                county=c["county"],
            ))
    pol = pd.DataFrame(pol_rows)

    claim_rows = []
    for i in range(4000):
        p = pol.sample(1).iloc[0]; s = datetime.fromisoformat(p["start_date"])
        days = random.randint(0,365); d = (s+timedelta(days=days)).date()
        amt = round(float(np.random.lognormal(mean=np.log(BASE[p["product_type"]]), sigma=1.0)),2)
        claim_rows.append(dict(
            claim_id=f"CLM-{i:06d}", policy_id=p["policy_id"], customer_id=p["customer_id"],
            vehicle_id=p["vehicle_id"], provider_id=random.choice(PROVIDERS),
            claim_date=d.isoformat(), claim_type=p["product_type"], claim_amount=amt,
            approved_amount=round(amt*random.uniform(0.5,0.95),2),
            paid_amount=round(amt*random.uniform(0.4,0.90),2),
            status=random.choices(["Paid","Approved","Submitted","Rejected"],weights=[0.6,0.15,0.15,0.10])[0],
            county=p["county"], development_month=days//30,
        ))
    claims = pd.DataFrame(claim_rows)

    pay_rows = []
    for i, c in claims.iterrows():
        if c["status"] != "Paid": continue
        pd_ = datetime.fromisoformat(c["claim_date"]) + timedelta(days=random.randint(1,45))
        pay_rows.append(dict(
            payment_id=f"PAY-{i:06d}", claim_id=c["claim_id"], amount=c["paid_amount"],
            payment_date=pd_.date().isoformat(),
            method=random.choice(["M-PESA","Bank","Cheque"]), status="Completed",
        ))
    pays = pd.DataFrame(pay_rows)

    prov = pd.DataFrame([dict(provider_id=x, name=f"Provider {x[-4:]}",
                              county=random.choice(COUNTIES),
                              tier=random.choice(["Tier 1","Tier 2","Tier 3"]))
                        for x in PROVIDERS])

    write(cust,   "silver/customer/part-0.parquet")
    write(pol,    "silver/policy/part-0.parquet")
    write(claims, "silver/claim/part-0.parquet")
    write(pays,   "silver/payment/part-0.parquet")
    write(prov,   "silver/provider/part-0.parquet")
    print("[seed-local] done -> next: STORAGE_MODE=local make pipeline")


if __name__ == "__main__":
    main()
