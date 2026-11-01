"""Insurelake read API: gold parquet -> JSON for the Next.js dashboard."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(os.environ.get("INSURLAKE_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "data"
GOLD = DATA / "gold"
QUALITY_JSON = ROOT / "governance" / "quality_report.json"
APRIORI_ELR = float(os.environ.get("INSURLAKE_APRIORI_ELR", "0") or 0.0)

app = FastAPI(title="Insurelake API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3000",
        "http://localhost:8501",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

CON = duckdb.connect(database=":memory:")


def _missing(msg: str) -> HTTPException:
    return HTTPException(status_code=404, detail=msg)


def _read(path: Path) -> pd.DataFrame | None:
    try:
        if path.is_file() and path.suffix == ".parquet":
            return CON.execute(f"select * from read_parquet('{path.as_posix()}')").df()
        if path.is_dir():
            if not any(path.glob("*.parquet")):
                return None
            glob = (path / "*.parquet").as_posix()
            return CON.execute(f"select * from read_parquet('{glob}')").df()
    except Exception:
        return None
    return None


def _table(name: str) -> pd.DataFrame | None:
    stem = name.split(".")[-1]
    for cand in (GOLD / f"{name}.parquet", GOLD / name, GOLD / f"{stem}.parquet", GOLD / stem):
        df = _read(cand)
        if df is not None and not df.empty:
            return df
    return None


def _col(df: pd.DataFrame | None, *names: str) -> str | None:
    if df is None:
        return None
    lower = {str(c).lower(): c for c in df.columns}
    for n in names:
        hit = lower.get(n.lower())
        if hit is not None:
            return hit
    return None


def _num(df, *names, default=0.0) -> pd.Series:
    c = _col(df, *names)
    if c is None:
        return pd.Series([default] * len(df), index=df.index, dtype="float64")
    return pd.to_numeric(df[c], errors="coerce").fillna(default)


def _txt(df, *names, default="") -> pd.Series:
    c = _col(df, *names)
    if c is None:
        return pd.Series([default] * len(df), index=df.index, dtype="object")
    return df[c].astype(str).fillna(default)


def _dates(df, *names) -> pd.Series:
    c = _col(df, *names)
    if c is None:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    return pd.to_datetime(df[c], errors="coerce")


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _claims() -> pd.DataFrame:
    facts = _table("fact_claims")
    if facts is None:
        raise _missing("gold.fact_claims missing - run: make pipeline")
    for dim, key in (
        ("dim_policy", "policy_id"),
        ("dim_county", "county_id"),
        ("dim_customer", "customer_id"),
    ):
        d = _table(dim)
        if d is None:
            continue
        dk = _col(d, key, key.replace("_", ""))
        fk = _col(facts, key, key.replace("_", ""))
        if not dk or not fk:
            continue
        extra = [c for c in d.columns if c not in facts.columns and c != dk]
        if not extra:
            continue
        try:
            facts = facts.merge(d[[dk] + extra], left_on=fk, right_on=dk, how="left")
        except Exception:
            continue
    return facts


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "root": str(ROOT),
        "gold": GOLD.exists(),
        "quality_report": QUALITY_JSON.exists(),
        "apriori_elr": APRIORI_ELR,
    }


@app.get("/executive/summary")
def executive_summary() -> dict[str, Any]:
    claims = _claims()
    policies = _table("dim_policy")
    ibnr = _table("ibnr_by_cohort")

    amount = _num(claims, "claim_amount", "amount", "incurred", "total_incurred")
    incurred = float(amount.sum())
    score = _num(claims, "fraud_score", "score", "risk_score", default=0.0)
    fraud = float(amount[score >= 0.75].sum())

    out: dict[str, Any] = {
        "incurred_claims_kes": round(incurred, 2),
        "fraud_exposure_kes": round(fraud, 2),
        "deltas": {"premium": 0.0, "claims": 0.0, "loss_ratio_pp": 0.0,
                   "fraud": 0.0, "ibnr": 0.0, "retention_pp": 0.0},
        "basis": "gold.fact_claims",
    }
    if ibnr is not None:
        out["ibnr_kes"] = round(float(_num(ibnr, "ibnr", "ibnr_kes", "reserve").sum()), 2)
    if policies is not None:
        premium = float(_num(policies, "premium", "written_premium",
                             "gross_premium", "premium_kes").sum())
        if premium > 0:
            out["earned_premium_kes"] = round(premium, 2)
            out["loss_ratio"] = round(incurred / premium, 4)
    return out


@app.get("/executive/premium-vs-claims")
def premium_vs_claims() -> list[dict]:
    claims = _claims()
    cd = _dates(claims, "claim_date", "filed_at", "incident_date", "created_at")
    camt = _num(claims, "claim_amount", "amount", "incurred", "total_incurred")

    prem = pd.Series(dtype="float64")
    policies = _table("dim_policy")
    if policies is not None:
        pdates = _dates(policies, "inception_date", "start_date",
                        "effective_date", "created_at")
        pamt = _num(policies, "premium", "written_premium",
                    "gross_premium", "premium_kes")
        if pdates.notna().any():
            prem = pamt.groupby(pdates.dt.strftime("%b")).sum()

    csum = pd.Series(dtype="float64")
    if cd.notna().any():
        csum = camt.groupby(cd.dt.strftime("%b")).sum()

    months = [m for m in MONTHS if m in set(prem.index) | set(csum.index)]
    if not months:
        raise _missing("no dated premium or claims in gold")
    return [
        {"month": m,
         "premium": round(float(prem.get(m, 0.0)), 2),
         "claims": round(float(csum.get(m, 0.0)), 2)}
        for m in months
    ]


@app.get("/fraud/distribution")
def fraud_distribution() -> list[dict]:
    claims = _claims()
    score = _num(claims, "fraud_score", "score", "risk_score",
                 default=float("nan")).dropna()
    if score.empty:
        raise _missing("no fraud_score in gold.fact_claims - run: make train")
    buckets = [
        ("CRITICAL", score >= 0.85),
        ("HIGH", (score >= 0.65) & (score < 0.85)),
        ("MEDIUM", (score >= 0.40) & (score < 0.65)),
        ("LOW", score < 0.40),
    ]
    return [{"level": name, "count": int(mask.sum())} for name, mask in buckets]


@app.get("/geo/county-risk")
def county_risk() -> list[dict]:
    claims = _claims()
    county = _txt(claims, "county_name", "county", "name")
    amount = _num(claims, "claim_amount", "amount", "incurred", "total_incurred")
    if (county == "").all():
        kpi = _table("county_kpi")
        if kpi is None:
            raise _missing("no county column and no gold.county_kpi")
        county = _txt(kpi, "county_name", "county", "name")
        amount = _num(kpi, "exposure", "premium", "amount", "exposure_kes")
    frame = pd.DataFrame({"county": county, "amount": amount, "one": 1.0})
    frame = frame[frame["county"] != ""]
    if frame.empty:
        raise _missing("no county rows in gold")
    agg = frame.groupby("county").agg(exposure=("amount", "sum"),
                                      claims=("one", "sum")).reset_index()
    top = agg.sort_values("exposure", ascending=False).head(47)
    hi = float(top["exposure"].max()) or 1.0
    return [
        {"county": str(r.county), "exposure_kes": round(float(r.exposure), 2),
         "claims": int(r.claims), "risk": round(float(r.exposure) / hi, 4)}
        for r in top.itertuples()
    ]


@app.get("/portfolio/lob-mix")
def lob_mix() -> list[dict]:
    policies = _table("dim_policy")
    if policies is None:
        raise _missing("gold.dim_policy missing - run: make pipeline")
    lob = _txt(policies, "lob", "line_of_business", "class_of_business",
               "product", default="Other")
    prem = _num(policies, "premium", "written_premium", "gross_premium", "premium_kes")
    agg = prem.groupby(lob).sum().sort_values(ascending=False)
    total = float(agg.sum())
    if total <= 0:
        raise _missing("no premium column in gold.dim_policy")
    return [
        {"lob": str(k), "premium_kes": round(float(v), 2),
         "share": round(float(v) / total, 4)}
        for k, v in agg.items()
    ]


@app.get("/payments/breakdown")
def payments_breakdown() -> list[dict]:
    pay = _table("fact_payments")
    if pay is None:
        raise _missing("gold.fact_payments missing - run: make pipeline")
    channel = _txt(pay, "channel", "payment_method", "method", default="Other")
    amt = _num(pay, "amount", "payment_amount", "amount_kes")
    agg = amt.groupby(channel).sum().sort_values(ascending=False)
    total = float(agg.sum())
    if total <= 0:
        raise _missing("no amount column in gold.fact_payments")
    return [
        {"channel": str(k), "amount_kes": round(float(v), 2),
         "share": round(float(v) / total, 4)}
        for k, v in agg.items()
    ]


def _layer(path: Path) -> dict:
    rows = 0
    size = 0
    tables = 0
    if path.exists():
        files = sorted(path.rglob("*.parquet"))
        groups: dict[str, list[Path]] = {}
        for f in files:
            rel = f.relative_to(path)
            key = rel.parent.as_posix() if rel.parent.as_posix() != "." else f.stem
            groups.setdefault(key, []).append(f)
        tables = len(groups)
        for fs in groups.values():
            size += sum(f.stat().st_size for f in fs)
            try:
                joined = "[" + ",".join(f"'{f.as_posix()}'" for f in fs) + "]"
                rows += int(CON.execute(
                    f"select count(*) from read_parquet({joined})").fetchone()[0])
            except Exception:
                continue
    return {"rows": rows, "size_gb": round(size / (1024 ** 3), 2), "tables": tables}


@app.get("/lakehouse/layers")
def lakehouse_layers() -> list[dict]:
    out = [{"layer": name, **_layer(DATA / name)} for name in ("bronze", "silver", "gold")]
    if not any(o["rows"] for o in out):
        raise _missing("no parquet under data/{bronze,silver,gold}")
    return out


@app.get("/governance/quality")
def governance_quality() -> dict:
    if not QUALITY_JSON.exists():
        raise _missing("governance/quality_report.json missing - run: make quality")
    report = json.loads(QUALITY_JSON.read_text(encoding="utf-8"))
    checks = []
    for c in report.get("checks", []):
        name = str(c.get("name") or c.get("check") or "check")
        ok = bool(c.get("success", c.get("passed", c.get("status") == "pass")))
        checks.append({"name": name,
                       "status": "pass" if ok else "warn",
                       "score": round(float(c.get("score", 1.0 if ok else 0.0)), 4)})
    score = float(report.get("overall_score", report.get("score", 0.0)))
    return {
        "score": round(score, 4),
        "evaluated": int(report.get("evaluated", len(checks))),
        "successful": int(report.get("successful",
                                     sum(1 for c in checks if c["status"] == "pass"))),
        "checks": checks,
    }


STATUS_MAP = {
    "open": "OPEN", "reported": "OPEN", "new": "OPEN",
    "review": "REVIEW", "investigating": "REVIEW", "pending": "REVIEW",
    "settled": "SETTLED", "paid": "SETTLED", "closed": "SETTLED",
    "declined": "DECLINED", "rejected": "DECLINED",
}


@app.get("/claims/recent")
def claims_recent(limit: int = Query(12, ge=1, le=200)) -> list[dict]:
    claims = _claims()
    frame = pd.DataFrame({
        "claim_id": _txt(claims, "claim_id", "id"),
        "policy_id": _txt(claims, "policy_id", "policyid"),
        "county": _txt(claims, "county_name", "county", default="Unknown"),
        "lob": _txt(claims, "lob", "line_of_business", "class_of_business", default="Motor"),
        "amount": _num(claims, "claim_amount", "amount", "incurred", "total_incurred"),
        "status": _txt(claims, "status", "claim_status", default="open")
        .str.lower().map(STATUS_MAP).fillna("OPEN"),
        "score": _num(claims, "fraud_score", "score", "risk_score", default=0.0),
        "filed": _dates(claims, "filed_at", "claim_date", "incident_date", "created_at"),
    })
    frame = frame.sort_values("filed", ascending=False, na_position="last").head(limit)
    if frame.empty:
        raise _missing("no claims in gold.fact_claims")
    return [
        {"claim_id": str(r.claim_id), "policy_id": str(r.policy_id),
         "county": str(r.county), "lob": str(r.lob),
         "amount_kes": round(float(r.amount), 2), "status": str(r.status),
         "fraud_score": round(float(r.score), 4),
         "filed_at": r.filed.isoformat() if pd.notna(r.filed) else ""}
        for r in frame.itertuples()
    ]


@app.get("/claims/intensity")
def claims_intensity() -> list[dict]:
    claims = _claims()
    filed = _dates(claims, "claim_date", "filed_at", "incident_date", "created_at")
    if not filed.notna().any():
        raise _missing("no date column in gold.fact_claims")
    score = _num(claims, "fraud_score", "score", "risk_score", default=0.0)
    frame = pd.DataFrame({"m": filed.dt.strftime("%b"),
                          "flag": (score >= 0.65).astype(int), "one": 1})
    agg = frame.dropna(subset=["m"]).groupby("m").agg(
        claims=("one", "sum"), flagged=("flag", "sum"))
    return [
        {"month": m, "claims": int(agg.loc[m, "claims"]),
         "flagged": int(agg.loc[m, "flagged"])}
        for m in MONTHS if m in agg.index
    ]


@app.get("/actuarial/ibnr-by-method")
def ibnr_by_method() -> list[dict]:
    df = _table("ibnr_by_cohort")
    if df is None:
        raise _missing("gold/actuarial/ibnr_by_cohort missing - run: make actuarial")
    ibnr = _num(df, "ibnr", "ibnr_kes", "reserve")
    total = float(ibnr.sum())
    n = len(ibnr)
    se = abs(float(ibnr.std(ddof=1))) * (n ** 0.5) if n > 1 else total * 0.15
    out = [{"method": "Chain Ladder", "ibnr_kes": round(total, 2),
            "se_kes": round(se, 2)}]

    reported = _num(df, "reported", "reported_to_date", "incurred",
                    default=float("nan"))
    premium = _num(df, "premium", "earned_premium", "premium_kes",
                   default=float("nan"))
    if reported.notna().all() and premium.notna().all() and float(premium.sum()) > 0:
        ult = reported + ibnr
        cdf = (ult / reported.replace(0, float("nan"))).fillna(1.0)
        unreported = (1.0 - 1.0 / cdf).clip(lower=0.0)
        elr_cc = float(reported.sum() / premium.sum())

        cc = (premium * elr_cc * unreported).clip(lower=0.0)
        out.append({"method": "Cape Cod", "ibnr_kes": round(float(cc.sum()), 2),
                    "se_kes": round(abs(float(cc.std(ddof=1))) * (n ** 0.5), 2)
                    if n > 1 else round(float(cc.sum()) * 0.17, 2)})

        if APRIORI_ELR > 0:
            bf = (premium * APRIORI_ELR * unreported).clip(lower=0.0)
            out.append({"method": "Bornhuetter-Ferguson",
                        "ibnr_kes": round(float(bf.sum()), 2),
                        "se_kes": round(abs(float(bf.std(ddof=1))) * (n ** 0.5), 2)
                        if n > 1 else round(float(bf.sum()) * 0.12, 2)})
    return out


@app.get("/executive/narrative")
def executive_narrative() -> list[dict]:
    claims = _claims()
    amount = _num(claims, "claim_amount", "amount", "incurred", "total_incurred")
    incurred = float(amount.sum())
    score = _num(claims, "fraud_score", "score", "risk_score", default=0.0)
    flagged = int((score >= 0.65).sum())
    total = int(len(claims))
    share = (flagged / total * 100.0) if total else 0.0

    county = _txt(claims, "county_name", "county", default="")
    top = county[county != ""].value_counts().head(3).index.tolist()

    ibnr_tbl = _table("ibnr_by_cohort")
    cohorts = 0 if ibnr_tbl is None else int(len(ibnr_tbl))
    ibnr = 0.0 if ibnr_tbl is None else float(
        _num(ibnr_tbl, "ibnr", "ibnr_kes", "reserve").sum())

    return [
        {"title": "Claims activity on the book",
         "body": "{:,} claims sit in gold.fact_claims carrying KSh {:,.1f}M incurred. "
                 "Densest counties: {}.".format(
                     total, incurred / 1e6, ", ".join(top) if top else "not populated")},
        {"title": "Fraud signal",
         "body": "{:,} claims score at or above 0.65 ({:.1f}% of the book). "
                 "These are the rows the streaming scorer sends to review.".format(
                     flagged, share)},
        {"title": "Reserves",
         "body": "Chain ladder IBNR is KSh {:,.1f}M across {} cohorts. "
                 "Read it against the Cape Cod estimate in the reserving panel "
                 "before sign-off.".format(ibnr / 1e6, cohorts)},
    ]


@app.get("/events/ticker")
def events_ticker() -> list[dict]:
    stamps = []
    for layer in ("bronze", "silver", "gold"):
        base = DATA / layer
        if not base.exists():
            continue
        files = sorted(base.rglob("*.parquet"),
                       key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        for f in files:
            st = f.stat()
            stamps.append((st.st_mtime, "pipeline.commit", "info",
                           "{} written ({} KB)".format(
                               f.relative_to(DATA).as_posix(),
                               int(st.st_size / 1024))))
    if QUALITY_JSON.exists():
        try:
            rep = json.loads(QUALITY_JSON.read_text(encoding="utf-8"))
            score = float(rep.get("overall_score", rep.get("score", 0.0)))
            stamps.append((QUALITY_JSON.stat().st_mtime, "dq.check",
                           "warn" if score < 0.95 else "info",
                           "quality report score {:.3f}".format(score)))
        except Exception:
            stamps.append((QUALITY_JSON.stat().st_mtime, "dq.check", "info",
                           "quality report updated"))
    model = ROOT / "ml" / "models" / "fraud_xgb.pkl"
    if model.exists():
        stamps.append((model.stat().st_mtime, "model.artifact", "info",
                       "fraud_xgb.pkl trained"))
    stamps.sort(reverse=True)
    if not stamps:
        raise _missing("no pipeline artifacts - run: make pipeline")
    return [
        {"id": "evt-{}".format(i), "ts": pd.Timestamp(ts, unit="s", tz="UTC").isoformat(),
         "kind": kind, "severity": sev, "message": msg}
        for i, (ts, kind, sev, msg) in enumerate(stamps[:16])
    ]
