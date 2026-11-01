import pandas as pd
from pipeline._storage import read_parquet, write_parquet, mode


def build_triangle(df):
    df = df.copy()
    df["claim_date"] = pd.to_datetime(df["claim_date"])
    df["cohort"] = df["claim_date"].dt.to_period("M").astype(str)
    return (df.pivot_table(index="cohort", columns="dev_month",
                           values="paid_amount", aggfunc="sum", fill_value=0)
              .sort_index().cumsum(axis=1))


def chain_ladder(tri):
    n = tri.shape[1]; factors = {}
    for d in range(n - 1):
        a, b = tri.iloc[:, d], tri.iloc[:, d + 1]
        mask = a > 0
        factors[d] = float(b[mask].sum() / a[mask].sum()) if mask.any() else 1.0
    cdfs = {}; cum = 1.0
    for d in reversed(range(n)):
        cum *= factors.get(d, 1.0)
        cdfs[d] = cum
    rows = []
    for cohort, row in tri.iterrows():
        active = row[row > 0]
        last   = int(active.index.max()) if not active.empty else 0
        paid   = float(active.iloc[-1]) if not active.empty else 0.0
        cdf    = cdfs.get(last, 1.0)
        rows.append(dict(cohort=cohort, latest_dev=last, paid_to_date=paid,
                         cdf=round(cdf, 4), ultimate=round(paid * cdf, 2),
                         ibnr=round(paid * (cdf - 1.0), 2)))
    return {"triangle": tri, "reserves": pd.DataFrame(rows)}


def main():
    print(f"[chain-ladder] storage: {mode()}")
    df = read_parquet("gold/claims_development")
    if df is None or df.empty:
        print("[chain-ladder] gold/claims_development empty - run `make pipeline` first"); return
    df = df[pd.to_numeric(df["paid_amount"], errors="coerce").fillna(0) > 0]
    if df.empty:
        print("[chain-ladder] no paid claims - can't build triangle"); return

    result = chain_ladder(build_triangle(df))
    write_parquet(result["reserves"].reset_index(drop=True), "gold/actuarial/ibnr_by_cohort/part-0.parquet")
    write_parquet(result["triangle"].reset_index(),         "gold/actuarial/triangle/part-0.parquet")

    print(f"\n=== Chain Ladder ===\nTotal IBNR: KSh {result['reserves']['ibnr'].sum():,.0f}\n")
    print(result["reserves"].to_string(index=False))


if __name__ == "__main__":
    main()
