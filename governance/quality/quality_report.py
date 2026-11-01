import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from pipeline._storage import read_parquet, write_parquet, mode


def _or_empty(df): return df if df is not None else pd.DataFrame()


def main():
    print(f"[quality] storage: {mode()}")
    claims    = _or_empty(read_parquet("silver/claim"))
    customers = _or_empty(read_parquet("silver/customer"))
    policies  = _or_empty(read_parquet("silver/policy"))
    payments  = _or_empty(read_parquet("silver/payment"))

    checks = {}
    checks["claims_completeness"]    = float(1 - claims["claim_amount"].isna().mean()) if not claims.empty and "claim_amount" in claims else 0.0
    checks["customers_completeness"] = float(1 - customers["phone"].isna().mean()) if not customers.empty and "phone" in customers else 0.0
    if not payments.empty and "amount" in payments.columns:
        amt = pd.to_numeric(payments["amount"], errors="coerce")
        checks["payments_validity"] = float(((amt > 0) & (amt < 1e9)).mean())
    else:
        checks["payments_validity"] = 0.0
    checks["duplicate_records"] = float(1 - claims["claim_id"].nunique() / max(len(claims), 1)) if not claims.empty and "claim_id" in claims else 0.0
    if not claims.empty and not policies.empty and "policy_id" in claims.columns:
        checks["policy_orphans"] = int((~claims["policy_id"].isin(policies["policy_id"])).sum())
    else:
        checks["policy_orphans"] = 0

    scored = [
        checks["claims_completeness"], checks["customers_completeness"],
        checks["payments_validity"], 1 - checks["duplicate_records"],
        1.0 if checks["policy_orphans"] == 0 else 0.0,
    ]
    overall = round(sum(scored) / len(scored), 4)

    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "overall_score": overall,
              "checks": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in checks.items()}}

    out = Path("governance") / "quality_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[quality] wrote {out}")

    write_parquet(pd.DataFrame([{"generated_at": report["generated_at"],
                                 "overall_score": report["overall_score"], **checks}]),
                  "gold/governance/quality_report/part-0.parquet")

    print(f"\n=== Data Quality ===\nOverall: {overall*100:.2f}%")
    for k, v in report["checks"].items():
        print(f"  {k:<24} {v}")


if __name__ == "__main__":
    main()
