"""INSURLAKE - Executive Control Centre (Vercel-style)
Light, card-based, shadcn-inspired. Reads ./data/gold/.
Run: streamlit run dashboard/app.py
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="INSURLAKE", page_icon="I",
                   layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------- CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, .stApp { font-family: 'Inter', -apple-system, sans-serif !important; }
.stApp { background: #f8fafc; }

[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e2e8f0; }
[data-testid="stSidebar"] * { color: #475569 !important; }
[data-testid="stSidebar"] [aria-checked="true"] + div p { color: #0f172a !important; font-weight: 600; }

h1, h2, h3, h4 { color: #0f172a !important; font-weight: 700; letter-spacing: -0.02em; }
p, span, div { color: #0f172a; }

.kpi-card { background:#fff; border:1px solid #e2e8f0; border-radius:12px;
            padding:1.15rem 1.3rem; box-shadow:0 1px 3px rgba(15,23,42,0.04); }
.kpi-label { color:#64748b; font-size:.75rem; font-weight:500;
             letter-spacing:.04em; text-transform:uppercase; }
.kpi-value { color:#0f172a; font-size:1.7rem; font-weight:700;
             margin-top:.3rem; line-height:1.1; letter-spacing:-.02em; }
.kpi-delta { font-size:.78rem; font-weight:600; margin-top:.45rem; }
.kpi-delta.up { color:#16a34a; } .kpi-delta.down { color:#ef4444; }
.kpi-delta.neu { color:#94a3b8; }

.badge { display:inline-block; padding:.12rem .55rem; border-radius:999px;
         font-size:.72rem; font-weight:600; }
.badge-critical { background:#fef2f2; color:#b91c1c; }
.badge-high     { background:#fff7ed; color:#c2410c; }
.badge-medium   { background:#eff6ff; color:#1d4ed8; }
.badge-low      { background:#f0fdf4; color:#15803d; }
.badge-success  { background:#f0fdf4; color:#15803d; }
.badge-muted    { background:#f1f5f9; color:#475569; }

.topbar { display:flex; align-items:center; justify-content:space-between;
          padding:.35rem 0 1.15rem 0; border-bottom:1px solid #e2e8f0;
          margin-bottom:1.25rem; }
.topbar-eyebrow { color:#64748b; font-size:.72rem; font-weight:600;
                  letter-spacing:.08em; text-transform:uppercase; }
.topbar-title   { color:#0f172a; font-size:1.5rem; font-weight:700;
                  margin-top:.1rem; letter-spacing:-.02em; }

.panel { background:#fff; border:1px solid #e2e8f0; border-radius:12px;
         padding:1.15rem 1.4rem 1.25rem; box-shadow:0 1px 3px rgba(15,23,42,.04);
         margin-bottom:1rem; }
.panel-title { font-size:.95rem; font-weight:600; color:#0f172a; margin:0; }
.panel-sub   { color:#64748b; font-size:.78rem; margin-top:.2rem; margin-bottom:.75rem; }

[data-testid="stDataFrame"] { border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; }
[data-testid="stMetricValue"] { font-family:'Inter',sans-serif !important; }

.stButton > button { background:#0f172a !important; color:#fff !important;
                     border:none !important; border-radius:8px !important;
                     font-weight:500 !important; }
.stButton > button:hover { background:#1e293b !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- constants
DATA_ROOT = Path(os.getenv("DATA_ROOT", "data"))

COUNTY_COORDS = {
    "Nairobi":    (-1.2921, 36.8219),  "Mombasa":    (-4.0435, 39.6682),
    "Kisumu":     (-0.0917, 34.7680),  "Nakuru":     (-0.3031, 36.0800),
    "Kiambu":     (-1.1714, 36.8356),  "Machakos":   (-1.5177, 37.2634),
    "Uasin Gishu":(0.5143, 35.2698),   "Kakamega":   (0.2827, 34.7519),
    "Meru":       (0.0463, 37.6559),   "Kajiado":    (-1.8524, 36.7768),
    "Kisii":      (-0.6817, 34.7667),  "Nyeri":      (-0.4169, 36.9513),
}

# ---------------------------------------------------------------- loaders
@st.cache_data(ttl=30)
def read_gold(rel: str) -> pd.DataFrame:
    root = DATA_ROOT / "gold" / rel
    if not root.exists(): return pd.DataFrame()
    files = list(root.rglob("*.parquet"))
    if not files: return pd.DataFrame()
    try: return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    except Exception as e:
        st.error(f"read {rel}: {e}"); return pd.DataFrame()


@st.cache_data(ttl=30)
def read_quality() -> dict:
    p = Path("governance/quality_report.json")
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: pass
    df = read_gold("governance/quality_report")
    if not df.empty: return df.iloc[0].to_dict()
    return {}


def norm(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    df = df.copy()
    for c in ["claim_amount", "premium", "paid_amount", "approved_amount"]:
        if c not in df.columns: df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if "fraud_score" not in df.columns: df["fraud_score"] = np.nan
    if "claim_date" in df.columns:
        df["claim_date"] = pd.to_datetime(df["claim_date"], errors="coerce")
        df = df.dropna(subset=["claim_date"])
    for c, default in [("county", "Unknown"), ("claim_type", "Unknown"),
                       ("status", "Unknown"), ("claim_id", "-")]:
        if c not in df.columns: df[c] = default
    return df

# ---------------------------------------------------------------- helpers
def fmt_money(v):
    v = float(v or 0)
    if abs(v) >= 1e9: return f"KSh {v/1e9:.2f}B"
    if abs(v) >= 1e6: return f"KSh {v/1e6:.2f}M"
    if abs(v) >= 1e3: return f"KSh {v/1e3:.1f}K"
    return f"KSh {v:,.0f}"

def fmt_pct(v, d=1): return f"{(v or 0)*100:.{d}f}%"

def topbar(title, eyebrow="Insurance Intelligence Platform", live=True):
    badge = "<span class='badge badge-success'>● Live</span>" if live else ""
    st.markdown(f"""
    <div class="topbar">
      <div>
        <div class="topbar-eyebrow">{eyebrow}</div>
        <div class="topbar-title">{title}</div>
      </div>
      <div style="text-align:right;">{badge}
        <span style="color:#94a3b8; font-size:.78rem; margin-left:.6rem;">
          Updated just now
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

def kpi(col, label, value, delta=None, delta_dir="neut", help=None):
    dl = ""
    if delta is not None:
        arrow = "▲" if delta_dir == "up" else "▼" if delta_dir == "down" else "◆"
        dl = f"<div class='kpi-delta {delta_dir}'>{arrow} {delta}</div>"
    col.markdown(
        f"<div class='kpi-card'>"
        f"<div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value'>{value}</div>{dl}</div>",
        unsafe_allow_html=True)

def panel_open(title, sub=""):
    st.markdown(
        f"<div class='panel'><div class='panel-title'>{title}</div>"
        f"<div class='panel-sub'>{sub}</div>", unsafe_allow_html=True)

def panel_close(): st.markdown("</div>", unsafe_allow_html=True)

def empty_state(msg, cmds):
    st.markdown(f"<div class='panel'><div class='panel-title'>{msg}</div></div>",
                unsafe_allow_html=True)
    st.code("\n".join(cmds), language="bash")

def style_fig(fig, h=340):
    fig.update_layout(
        template="plotly_white", height=h,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter", color="#334155", size=12),
        xaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0"),
        yaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0"),
    )
    return fig


def score_fraud(fact: pd.DataFrame) -> pd.DataFrame:
    df = fact.copy()
    risk = {"Nairobi":.8,"Mombasa":.8,"Kisumu":.75,"Nakuru":.7,"Kiambu":.7}
    df["cust_freq"] = (df.groupby("customer_id")["claim_id"]
                         .transform("count") if "customer_id" in df.columns else 1)
    df["prov_freq"] = (df.groupby("provider_id")["claim_id"]
                         .transform("count") if "provider_id" in df.columns else 1)
    s = (
        0.20*(df["claim_amount"] > df["claim_amount"].quantile(.95)).astype(float) +
        0.25*(df["cust_freq"] >= 3).astype(float) +
        0.20*(df["prov_freq"] >= 20).astype(float) +
        0.20* df["county"].map(risk).fillna(.2) +
        0.15*(df["status"] == "Submitted").astype(float)
    )
    df["_p"] = np.clip(s, 0, .99)
    df["_risk"] = np.select(
        [df["_p"] >= .80, df["_p"] >= .65, df["_p"] >= .45],
        ["CRITICAL", "HIGH", "MEDIUM"], default="LOW")
    return df

# ================================================================
# PAGE: Executive
# ================================================================
def page_executive():
    topbar("Executive Overview")
    fact = norm(read_gold("fact_claims"))
    if fact.empty:
        empty_state("No gold data. Run the pipeline first:",
                    ["python -m data_generator.seed_local",
                     "python -m pipeline.silver_to_gold",
                     "python -m actuarial.reserving.chain_ladder"]); return

    premium  = float(fact["premium"].sum())
    incurred = float(fact["claim_amount"].sum())
    paid     = float(fact["paid_amount"].sum())
    lr       = (paid/premium) if premium else 0

    # 30d deltas
    df_max = fact["claim_date"].max()
    l30 = fact[fact["claim_date"] >= df_max - pd.Timedelta(days=30)]
    p30 = fact[(fact["claim_date"] < df_max - pd.Timedelta(days=30)) &
               (fact["claim_date"] >= df_max - pd.Timedelta(days=60))]
    dp = l30["premium"].sum() - p30["premium"].sum()
    dc = l30["claim_amount"].sum() - p30["claim_amount"].sum()

    k1, k2, k3, k4 = st.columns(4)
    kpi(k1, "Premium",      fmt_money(premium),
        f"{fmt_pct(abs(dp)/max(premium,1))} vs prior 30d",
        "up" if dp >= 0 else "down")
    kpi(k2, "Claims Incurred", fmt_money(incurred),
        f"{fmt_pct(abs(dc)/max(incurred,1))} vs prior 30d",
        "down" if dc <= 0 else "up")
    kpi(k3, "Loss Ratio",   fmt_pct(lr),
        "on target" if lr < .70 else "above target",
        "up" if lr < .70 else "down")
    kpi(k4, "Total Claims", f"{len(fact):,}",
        f"{l30.shape[0]} in last 30d", "neu")

    # Trend + Map
    st.write("")
    col_trend, col_map = st.columns([1.55, 1])

    with col_trend:
        panel_open("Premium vs Claims", "Monthly, last 12 months")
        trend = (fact.assign(month=fact["claim_date"].dt.to_period("M").dt.to_timestamp())
                     .groupby("month", as_index=False)
                     .agg(premium=("premium","sum"),
                          incurred=("claim_amount","sum"),
                          paid=("paid_amount","sum"))
                     .sort_values("month").tail(12))
        fig = go.Figure()
        fig.add_trace(go.Bar(x=trend["month"], y=trend["premium"],
                             name="Premium", marker_color="#0f172a", opacity=.9,
                             width=12*86400000*.4))
        fig.add_trace(go.Bar(x=trend["month"], y=trend["incurred"],
                             name="Incurred", marker_color="#ef4444", opacity=.85,
                             width=12*86400000*.4))
        fig.add_trace(go.Scatter(x=trend["month"], y=trend["paid"],
                                 name="Paid", line=dict(color="#0ea5e9", width=2.5),
                                 mode="lines+markers",
                                 marker=dict(size=6, color="#0ea5e9")))
        fig.update_layout(barmode="group",
                          legend=dict(orientation="h", y=1.08, x=0,
                                      font=dict(size=11)))
        style_fig(fig, 300).update_xaxes(title="").update_yaxes(title="")
        st.plotly_chart(fig, use_container_width=True)
        panel_close()

    with col_map:
        panel_open("County Risk", "Bubble size = premium · color = loss ratio")
        county = read_gold("county_kpi")
        if county.empty:
            county = (fact.groupby("county", as_index=False)
                          .agg(total_premium=("premium","sum"),
                               total_paid=("paid_amount","sum")))
            county["loss_ratio"] = (county["total_paid"] /
                                    county["total_premium"].replace(0, np.nan))
        county = county.copy()
        county["lat"] = county["county"].map(lambda c: COUNTY_COORDS.get(c, (None,None))[0])
        county["lon"] = county["county"].map(lambda c: COUNTY_COORDS.get(c, (None,None))[1])
        county = county.dropna(subset=["lat","lon"])
        county["loss_ratio"] = pd.to_numeric(county["loss_ratio"], errors="coerce").fillna(0)
        county["total_premium"] = pd.to_numeric(
            county.get("total_premium", county.get("total_claims", 1)),
            errors="coerce").fillna(1)
        if not county.empty:
            fig = px.scatter_geo(
                county, lat="lat", lon="lon",
                size="total_premium", color="loss_ratio",
                hover_name="county",
                color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
                size_max=45, range_color=(0, 1.2),
            )
            fig.update_geos(
                center=dict(lat=-0.5, lon=37.8),
                projection_type="mercator",
                lataxis_range=[-5.5, 5.5], lonaxis_range=[33.5, 42.5],
                showcountries=True, countrycolor="#cbd5e1",
                showcoastlines=True, coastlinecolor="#94a3b8",
                showland=True, landcolor="#f1f5f9",
                showocean=True, oceancolor="#e0f2fe",
                showlakes=True, lakecolor="#e0f2fe",
            )
            fig.update_layout(
                template="plotly_white", height=300,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=0, b=0),
                font=dict(family="Inter", color="#334155", size=11),
                coloraxis_colorbar=dict(
                    title="Loss ratio", thickness=8, len=.7,
                    tickformat=".0%", ticks="outside",
                ),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No county data with known coordinates.")
        panel_close()

    # Bottom row: Counties table + Recent claims
    st.write("")
    col_b1, col_b2 = st.columns([1, 1.35])

    with col_b1:
        panel_open("Top Counties", "Ranked by loss ratio")
        cty = read_gold("county_kpi")
        if cty.empty:
            cty = (fact.groupby("county", as_index=False)
                       .agg(total_paid=("paid_amount","sum"),
                            total_premium=("premium","sum"),
                            total_claims=("claim_id","count")))
            cty["loss_ratio"] = cty["total_paid"] / cty["total_premium"].replace(0, np.nan)
        cty = cty.sort_values("loss_ratio", ascending=False).head(8)
        for _, r in cty.iterrows():
            lr_v = float(r["loss_ratio"]) if pd.notna(r["loss_ratio"]) else 0
            tone = ("badge-critical" if lr_v >= .9 else
                    "badge-high"     if lr_v >= .7 else
                    "badge-low")
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; "
                f"align-items:center; padding:.55rem 0; "
                f"border-bottom:1px solid #f1f5f9;'>"
                f"<span style='font-weight:500; color:#0f172a;'>{r['county']}</span>"
                f"<span class='badge {tone}'>{lr_v*100:.0f}%</span></div>",
                unsafe_allow_html=True)
        panel_close()

    with col_b2:
        panel_open("Recent Claims", "Latest 8 by date")
        recent = fact.sort_values("claim_date", ascending=False).head(8)
        rows = []
        for _, r in recent.iterrows():
            rows.append({
                "Claim ID": str(r.get("claim_id","-"))[:12],
                "Type":     r.get("claim_type","-"),
                "County":   r.get("county","-"),
                "Amount":   fmt_money(r.get("claim_amount",0)),
                "Status":   str(r.get("status","-")).title(),
                "Date":     r["claim_date"].date().isoformat() if pd.notna(r["claim_date"]) else "-",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True,
                     hide_index=True, height=290)
        panel_close()


# ================================================================
# PAGE: Claims
# ================================================================
def page_claims():
    topbar("Claims Analytics")
    fact = norm(read_gold("fact_claims"))
    if fact.empty: empty_state("No claims data.", ["python -m pipeline.silver_to_gold"]); return

    k1, k2, k3, k4 = st.columns(4)
    kpi(k1, "Total Claims", f"{len(fact):,}")
    kpi(k2, "Avg Claim",    fmt_money(fact["claim_amount"].mean()))
    kpi(k3, "Median Claim", fmt_money(fact["claim_amount"].median()))
    kpi(k4, "P95 Claim",    fmt_money(fact["claim_amount"].quantile(.95)))

    st.write("")
    col_a, col_b = st.columns([1.4, 1])

    with col_a:
        panel_open("Claim Amount Distribution", "Log-scaled · split by type")
        fig = px.histogram(fact, x="claim_amount", nbins=55,
                           color="claim_type", log_y=True)
        fig.update_layout(bargap=.05, legend=dict(orientation="h", y=1.1, x=0, font=dict(size=10)))
        style_fig(fig, 320).update_xaxes(title="Claim amount (KSh)").update_yaxes(title="log count")
        st.plotly_chart(fig, use_container_width=True)
        panel_close()

    with col_b:
        panel_open("Claim Type Mix", "By count")
        mix = fact.groupby("claim_type", as_index=False).agg(count=("claim_id","count"))
        fig = px.pie(mix, names="claim_type", values="count", hole=.55,
                     color_discrete_sequence=["#0f172a","#334155","#0ea5e9","#94a3b8","#f59e0b"])
        fig.update_traces(textposition="inside", textinfo="percent", textfont_size=11)
        style_fig(fig, 320).update_layout(legend=dict(orientation="h", y=-.15,
                                                      font=dict(size=10)), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        panel_close()

    st.write("")
    panel_open("Frequency vs Severity by County", "Each bubble = one county")
    agg = (fact.groupby("county", as_index=False)
               .agg(frequency=("claim_id","count"),
                    severity=("claim_amount","mean"),
                    total=("claim_amount","sum")))
    agg = agg[agg["frequency"] >= 3]
    fig = px.scatter(agg, x="frequency", y="severity", size="total", text="county",
                     color="severity", color_continuous_scale=["#dcfce7","#f59e0b","#ef4444"])
    fig.update_traces(textposition="top center", textfont=dict(size=10))
    style_fig(fig, 420).update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
    panel_close()


# ================================================================
# PAGE: Actuarial
# ================================================================
def page_actuarial():
    topbar("Actuarial Intelligence")
    ibnr = read_gold("actuarial/ibnr_by_cohort")
    dev  = read_gold("claims_development")

    if ibnr.empty and dev.empty:
        empty_state("No actuarial data yet:",
                    ["python -m pipeline.silver_to_gold",
                     "python -m actuarial.reserving.chain_ladder"]); return

    if not ibnr.empty:
        tot_ibnr = float(ibnr["ibnr"].sum())
        tot_ult = float(ibnr["ultimate"].sum()) if "ultimate" in ibnr.columns else tot_ibnr
        avg_cdf = float(ibnr["cdf"].mean()) if "cdf" in ibnr.columns else 1.0

        k1, k2, k3, k4 = st.columns(4)
        kpi(k1, "Cohorts",     f"{len(ibnr)}")
        kpi(k2, "Total IBNR",  fmt_money(tot_ibnr), "reserve held", "neu")
        kpi(k3, "Ultimate",    fmt_money(tot_ult))
        kpi(k4, "Avg CDF",     f"{avg_cdf:.3f}", "development factor", "neu")

    st.write("")
    if not dev.empty and "dev_month" in dev.columns:
        panel_open("Development Triangle", "Cumulative paid · cohort × development month")
        d = dev.copy()
        d["claim_date"] = pd.to_datetime(d["claim_date"], errors="coerce")
        d = d.dropna(subset=["claim_date"])
        d["cohort"] = d["claim_date"].dt.to_period("M").astype(str)
        d["dev_month"] = pd.to_numeric(d["dev_month"], errors="coerce").fillna(0).astype(int)
        d["paid_amount"] = pd.to_numeric(d["paid_amount"], errors="coerce").fillna(0)
        piv = d.pivot_table(index="cohort", columns="dev_month",
                            values="paid_amount", aggfunc="sum", fill_value=0).cumsum(axis=1)
        piv = piv.tail(18)
        fig = px.imshow(piv, aspect="auto", origin="lower",
                        color_continuous_scale=["#f1f5f9","#0ea5e9","#0f172a"],
                        labels=dict(x="Development month", y="Cohort", color="Paid"))
        style_fig(fig, 420)
        st.plotly_chart(fig, use_container_width=True)
        panel_close()

    if not ibnr.empty:
        st.write("")
        col_a, col_b = st.columns([1.5, 1])
        with col_a:
            panel_open("IBNR Reserves", "By cohort, stacked view")
            i = ibnr.sort_values("cohort").copy()
            i["paid"] = pd.to_numeric(i.get("paid_to_date",0), errors="coerce").fillna(0)
            i["ibnr"] = pd.to_numeric(i["ibnr"], errors="coerce").fillna(0)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=i["cohort"], y=i["paid"], name="Paid",
                                 marker_color="#0f172a"))
            fig.add_trace(go.Bar(x=i["cohort"], y=i["ibnr"], name="IBNR",
                                 marker_color="#f59e0b"))
            fig.update_layout(barmode="stack",
                              legend=dict(orientation="h", y=1.08, font=dict(size=11)))
            style_fig(fig, 340).update_xaxes(title="", tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            panel_close()

        with col_b:
            panel_open("Reserve Adequacy", "Top 6 cohorts by IBNR")
            top = ibnr.nlargest(6, "ibnr")
            for _, r in top.iterrows():
                st.markdown(
                    f"<div style='display:flex; justify-content:space-between; "
                    f"padding:.55rem 0; border-bottom:1px solid #f1f5f9;'>"
                    f"<span style='color:#0f172a; font-weight:500;'>"
                    f"{r['cohort']}</span>"
                    f"<span class='badge badge-medium'>{fmt_money(r['ibnr'])}</span></div>",
                    unsafe_allow_html=True)
            panel_close()


# ================================================================
# PAGE: Fraud
# ================================================================
def page_fraud():
    topbar("Fraud Intelligence")
    fact = norm(read_gold("fact_claims"))
    if fact.empty: empty_state("No claims.", ["python -m pipeline.silver_to_gold"]); return

    scored = score_fraud(fact)
    alerts = scored[scored["_risk"].isin(["CRITICAL","HIGH"])] \
                .sort_values("_p", ascending=False)

    k1, k2, k3, k4 = st.columns(4)
    kpi(k1, "Claims Scored", f"{len(scored):,}", "rule-based", "neu")
    kpi(k2, "Critical",      f"{int((scored['_risk']=='CRITICAL').sum())}",
        "action needed", "down")
    kpi(k3, "High",          f"{int((scored['_risk']=='HIGH').sum())}",
        "review", "down")
    kpi(k4, "Avg Risk",      fmt_pct(scored["_p"].mean()), "portfolio signal", "neu")

    st.write("")
    col_a, col_b = st.columns([1, 1.5])

    with col_a:
        panel_open("Risk Distribution", "By severity band")
        dist = scored["_risk"].value_counts().reindex(
            ["CRITICAL","HIGH","MEDIUM","LOW"]).fillna(0).astype(int)
        fig = go.Figure(go.Bar(
            x=dist.index, y=dist.values,
            marker_color=["#ef4444","#f59e0b","#0ea5e9","#22c55e"],
            text=dist.values, textposition="outside",
        ))
        style_fig(fig, 300).update_layout(
            margin=dict(l=0,r=0,t=30,b=0),
            xaxis=dict(title="", showgrid=False),
            yaxis=dict(title="", gridcolor="#f1f5f9"))
        st.plotly_chart(fig, use_container_width=True)
        panel_close()

    with col_b:
        panel_open("Alert Feed", f"Top {min(len(alerts), 15)} high-risk claims")
        shown = alerts.head(15)
        if shown.empty:
            st.info("No high-risk claims in current dataset.")
        else:
            for _, r in shown.iterrows():
                tone = "badge-" + r["_risk"].lower()
                st.markdown(
                    f"<div style='display:flex; justify-content:space-between; "
                    f"padding:.55rem .1rem; border-bottom:1px solid #f1f5f9; "
                    f"align-items:center;'>"
                    f"<span style='font-weight:500; color:#0f172a; min-width:90px;'>"
                    f"{str(r['claim_id'])[:12]}</span>"
                    f"<span style='color:#64748b; font-size:.85rem; flex:1; "
                    f"text-align:left; margin-left:.5rem;'>{r['county']} · "
                    f"{r['claim_type']}</span>"
                    f"<span style='font-family:Inter; color:#0f172a; "
                    f"min-width:90px; text-align:right;'>"
                    f"{fmt_money(r['claim_amount'])}</span>"
                    f"<span class='badge {tone}' style='margin-left:.75rem;'>"
                    f"{r['_risk']}</span>"
                    f"<span style='color:#94a3b8; font-size:.75rem; "
                    f"min-width:55px; text-align:right;'>"
                    f"p={r['_p']:.2f}</span></div>",
                    unsafe_allow_html=True)
        panel_close()


# ================================================================
# PAGE: Governance
# ================================================================
def page_quality():
    topbar("Governance & Data Quality")
    report = read_quality()
    if not report:
        empty_state("No quality report. Generate it:",
                    ["python -m governance.quality.quality_report"]); return

    score = float(report.get("overall_score", 0)) * 100
    checks = report.get("checks", {})
    passed = sum(1 for k, v in checks.items()
                 if isinstance(v, (int, float)) and
                 ((v >= .95) if "duplicate" not in k and "orphan" not in k
                  else (v <= .02 if "duplicate" in k else v == 0)))
    failed = len(checks) - passed

    k1, k2, k3, k4 = st.columns(4)
    kpi(k1, "Overall Score", f"{score:.1f}%",
        "healthy" if score >= 95 else "degraded",
        "up" if score >= 95 else "down")
    kpi(k2, "Total Checks",  f"{len(checks)}")
    kpi(k3, "Passing",       f"{passed}/{len(checks)}", "compliant", "up")
    kpi(k4, "Failing",       f"{failed}", "review", "down" if failed else "neu")

    st.write("")
    panel_open("Scorecard", "Per-check status")
    rows = []
    for k, v in checks.items():
        if not isinstance(v, (int, float)): continue
        if "duplicate" in k:
            ok, shown = v <= .02, f"{v*100:.2f}%"
        elif "orphan" in k:
            ok, shown = v == 0, f"{int(v)}"
        else:
            ok, shown = v >= .95, f"{v*100:.2f}%"
        rows.append({
            "Check": k.replace("_"," ").title(),
            "Value": shown,
            "Status": "PASS" if ok else "FAIL",
        })
    df = pd.DataFrame(rows)

    def tone(s):
        return "background-color:#f0fdf4; color:#15803d; font-weight:600;" \
            if s == "PASS" else "background-color:#fef2f2; color:#b91c1c; font-weight:600;"
    st.dataframe(df.style.applymap(tone, subset=["Status"]),
                 use_container_width=True, hide_index=True, height=310)
    panel_close()

    st.write("")
    panel_open("Pipeline Freshness", "Latest state of gold layer")
    fact = norm(read_gold("fact_claims"))
    c1, c2, c3 = st.columns(3)

    def metric_text(col, label, value):
        col.markdown(
            f"<div class='kpi-card' style='padding:.9rem 1.1rem;'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div style='color:#0f172a; font-weight:600; font-size:1.1rem; "
            f"margin-top:.3rem;'>{value}</div></div>",
            unsafe_allow_html=True)

    if not fact.empty:
        metric_text(c1, "Latest claim",    fact["claim_date"].max().date().isoformat())
        metric_text(c2, "Fact rows",       f"{len(fact):,}")
        metric_text(c3, "Distinct counties", f"{fact['county'].nunique()}")
    else:
        metric_text(c1, "Latest claim", "-")
        metric_text(c2, "Fact rows", "0")
        metric_text(c3, "Distinct counties", "0")
    panel_close()


# ================================================================
# Sidebar + router
# ================================================================
with st.sidebar:
    st.markdown(
        "<div style='padding:.5rem 0 1rem 0;'>"
        "<div style='color:#0f172a; font-size:1.1rem; font-weight:700; "
        "letter-spacing:-.02em;'>INSURLAKE</div>"
        "<div style='color:#64748b; font-size:.7rem; font-weight:600; "
        "letter-spacing:.08em; text-transform:uppercase; margin-top:.15rem;'>"
        "Control Centre</div></div>",
        unsafe_allow_html=True)
    st.markdown("<hr style='margin:0 0 .75rem 0; border:none; "
                "border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["Executive", "Claims", "Actuarial", "Fraud", "Governance"],
        label_visibility="collapsed")

    st.markdown("<hr style='margin:.75rem 0; border:none; "
                "border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:#94a3b8; font-size:.72rem; letter-spacing:.04em;"
        f" text-transform:uppercase; font-weight:600;'>Workspace</div>"
        f"<div style='color:#475569; font-size:.82rem; margin-top:.35rem;'>"
        f"{DATA_ROOT.resolve()}</div>",
        unsafe_allow_html=True)
    st.write("")
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


if   page == "Executive":  page_executive()
elif page == "Claims":     page_claims()
elif page == "Actuarial":  page_actuarial()
elif page == "Fraud":      page_fraud()
elif page == "Governance": page_quality()
