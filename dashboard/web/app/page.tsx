import { Banknote, Gauge, Layers, LineChart, ShieldAlert, Siren } from "lucide-react";

import { Badge, Kpi, Legend, Panel } from "@/components/panels";
import { ArcGauge, AreaTrend, BarList, Columns, Donut, HBar } from "@/components/charts";
import LiveEventTicker from "@/components/LiveEventTicker";
import { compact, count, kes, pct } from "@/lib/format";
import {
  claimsAndFraudIntensity,
  countyRisk,
  dataQuality,
  executiveNarrative,
  executiveSummary,
  fraudAlertDistribution,
  ibnrByMethod,
  layerCounts,
  lineOfBusinessMix,
  liveEvents,
  paymentsBreakdown,
  premiumVsClaimsTrend,
  recentClaims,
} from "@/lib/queries";

export const dynamic = "force-dynamic";

const CYAN = "#22d3ee";
const ROSE = "#f43f5e";
const GOLD = "#eab308";
const EMERALD = "#34d399";
const VIOLET = "#a78bfa";
const BRONZE = "#c9803f";

const LAYER_TONE: Record<string, string> = { bronze: BRONZE, silver: "#94a3b8", gold: GOLD };
const STATUS_TONE: Record<string, string> = {
  OPEN: CYAN,
  REVIEW: GOLD,
  SETTLED: EMERALD,
  DECLINED: ROSE,
};

const BADGES = [
  "Apache Iceberg v2",
  "Kafka (8 topics)",
  "Spark Structured Streaming",
  "dbt \u00B7 34 models",
  "Trino SQL",
  "MLflow",
  "Great Expectations",
  "OpenMetadata",
];

export default async function ExecutiveControlPage() {
  const [
    summary, trend, fraud, counties, lob, ibnr, payments,
    layers, dq, claims, intensity, narrative, events,
  ] = await Promise.all([
    executiveSummary(),
    premiumVsClaimsTrend(),
    fraudAlertDistribution(),
    countyRisk(),
    lineOfBusinessMix(),
    ibnrByMethod(),
    paymentsBreakdown(),
    layerCounts(),
    dataQuality(),
    recentClaims(12),
    claimsAndFraudIntensity(),
    executiveNarrative(),
    liveEvents(),
  ]);

  const lossTone = summary.loss_ratio > 0.7 ? ROSE : summary.loss_ratio > 0.6 ? GOLD : EMERALD;
  const totalLayerRows = layers.reduce((a, l) => a + l.rows, 0);
  const paymentsTotal = payments.reduce((a, p) => a + p.amount_kes, 0);
  const topCounties = counties.slice(0, 12);

  return (
    <main className="mx-auto max-w-[1640px] px-5 py-7 lg:px-8">
      <header className="mb-7 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="mono text-[15px] tracking-[0.18em] text-slate-100">
              INSURE<span className="text-cyanaccent">LAKE</span>
            </span>
            <span className="text-slate-600">{"\u00B7"}</span>
            <span className="text-[12.5px] text-slate-400">Executive Control Centre</span>
          </div>
          <nav className="mono mt-2 flex flex-wrap items-center gap-4 text-[10px] uppercase tracking-widest">
            <span className="text-cyanaccent">Executive</span>
            <a className="text-slate-500 transition hover:text-slate-300" href="#fraud">Fraud</a>
            <a className="text-slate-500 transition hover:text-slate-300" href="#actuarial">Actuarial</a>
            <a className="text-slate-500 transition hover:text-slate-300" href="#governance">Governance</a>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <Badge>{"\u25C8"} governed lakehouse</Badge>
          <span className="mono text-[10px] text-slate-500">v2.4.1</span>
        </div>
      </header>

      <section className="mb-6">
        <p className="mono text-[10px] uppercase tracking-[0.28em] text-cyanaccent">
          {"\u25C8"} Insurance data intelligence platform
        </p>
        <p className="mt-2 max-w-4xl text-[13px] leading-relaxed text-slate-400">
          A real-time, governed insurance lakehouse powering actuarial analytics, fraud
          intelligence, risk modelling and executive decision-making across 47 Kenyan counties.
        </p>
        <div className="mt-4 flex flex-wrap gap-1.5">
          {BADGES.map((b) => <Badge key={b}>{b}</Badge>)}
        </div>
      </section>

      <section className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Earned premium" value={kes(summary.earned_premium_kes)} sub="YTD, all classes"
          tone={CYAN} delta={summary.deltas.premium} Icon={Banknote} />
        <Kpi label="Incurred claims" value={kes(summary.incurred_claims_kes)} sub="YTD, gross of recoveries"
          tone={ROSE} delta={summary.deltas.claims} Icon={Siren} />
        <Kpi label="Loss ratio" value={pct(summary.loss_ratio)} sub="Incurred / earned"
          tone={lossTone} delta={summary.deltas.loss_ratio_pp} deltaSuffix="pp" Icon={Gauge} />
        <Kpi label="Fraud exposure" value={kes(summary.fraud_exposure_kes)} sub="Flagged, not yet recovered"
          tone={GOLD} delta={summary.deltas.fraud} Icon={ShieldAlert} />
        <Kpi label="IBNR reserve" value={kes(summary.ibnr_kes)} sub="Chain ladder central"
          tone={VIOLET} delta={summary.deltas.ibnr} Icon={LineChart} />
        <Kpi label="Retention" value={pct(summary.retention_rate)} sub="Net written / gross"
          tone={EMERALD} delta={summary.deltas.retention_pp} deltaSuffix="pp" Icon={Layers} />
      </section>

      <div className="grid grid-cols-12 gap-4">
        <Panel title="Premium vs claims trend" accent={CYAN} badge={"\u{1F947} gold"}
          className="col-span-12 xl:col-span-8">
          <div className="mb-2 flex items-center gap-4">
            <Legend color={CYAN} label="Earned premium" />
            <Legend color={ROSE} label="Incurred claims" />
            <span className="mono ml-auto text-[9.5px] text-slate-500">KES, monthly</span>
          </div>
          <div className="h-[210px]">
            <AreaTrend
              labels={trend.map((t) => t.month)}
              series={[
                { key: "premium", label: "Earned premium", color: CYAN, values: trend.map((t) => t.premium) },
                { key: "claims", label: "Incurred claims", color: ROSE, values: trend.map((t) => t.claims) },
              ]}
            />
          </div>
        </Panel>

        <Panel title="Fraud alert distribution" accent={ROSE}
          link={{ label: "console", href: "#fraud" }} className="col-span-12 md:col-span-6 xl:col-span-4">
          <BarList
            items={fraud.map((f) => ({ label: f.level, value: f.count, note: count(f.count) }))}
            color={ROSE}
          />
          <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-2.5">
            <span className="text-[10px] uppercase tracking-widest text-slate-500">Total flagged</span>
            <span className="mono text-[11.5px] text-slate-200">
              {count(fraud.reduce((a, f) => a + f.count, 0))}
            </span>
          </div>
        </Panel>

        <Panel title="County insurance risk map" accent={GOLD} badge="Kenya"
          className="col-span-12 md:col-span-6 xl:col-span-5">
          <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-4">
            {topCounties.map((c) => (
              <div key={c.county} className="rounded-md border border-slate-800 bg-slate-950/50 px-2 py-1.5"
                title={`${c.county} - ${c.claims} claims`}>
                <p className="truncate text-[10.5px] text-slate-300">{c.county}</p>
                <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full"
                    style={{ width: `${Math.round(c.risk * 100)}%`, background: GOLD }} />
                </div>
                <p className="mono mt-1 text-[9px] text-slate-500">{kes(c.exposure_kes, 0)}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[9.5px] text-slate-500">
            Top 12 of {counties.length} counties by exposure. Bar = composite risk index.
          </p>
        </Panel>

        <Panel title="Line of business mix" accent={CYAN} className="col-span-12 md:col-span-6 xl:col-span-4">
          <Donut
            items={lob.map((l) => ({ label: l.lob, share: l.share }))}
            palette={[CYAN, VIOLET, EMERALD, GOLD, BRONZE, "#94a3b8", ROSE]}
            centerLabel="premium"
            centerValue={kes(summary.earned_premium_kes, 1)}
          />
        </Panel>

        <Panel id="actuarial" title="Reserving: IBNR by method" accent={VIOLET}
          link={{ label: "actuarial", href: "#actuarial" }} className="col-span-12 md:col-span-6 xl:col-span-3">
          <HBar
            items={ibnr.map((m) => ({
              label: m.method,
              value: m.ibnr_kes,
              note: `Mack SE ${kes(m.se_kes, 0)}`,
            }))}
            color={VIOLET}
            formatValue={(v) => kes(v, 0)}
          />
        </Panel>

        <Panel title="Payments and M-PESA" accent={EMERALD} className="col-span-12 md:col-span-6 xl:col-span-4">
          <Donut
            items={payments.map((p) => ({ label: p.channel, share: p.share }))}
            palette={[EMERALD, CYAN, VIOLET, "#94a3b8"]}
            centerLabel="settled"
            centerValue={kes(paymentsTotal, 1)}
          />
        </Panel>

        <Panel title="Lakehouse volume by layer" accent={BRONZE} className="col-span-12 md:col-span-6 xl:col-span-4">
          <ul className="space-y-2.5">
            {layers.map((l) => (
              <li key={l.layer} className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-[11.5px] uppercase tracking-widest text-slate-300">
                    <span className="h-2 w-2 rounded-sm" style={{ background: LAYER_TONE[l.layer] }} />
                    {l.layer}
                  </span>
                  <span className="mono text-[10.5px] text-slate-400">{compact(l.rows)} rows</span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full"
                    style={{ width: `${Math.max(4, (l.rows / totalLayerRows) * 100)}%`, background: LAYER_TONE[l.layer] }} />
                </div>
                <div className="mono mt-1.5 flex items-center justify-between text-[9.5px] text-slate-500">
                  <span>{l.tables} tables</span>
                  <span>{l.size_gb.toFixed(1)} GB</span>
                </div>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel id="governance" title="Data quality and trust" accent={EMERALD}
          link={{ label: "governance", href: "#governance" }} className="col-span-12 md:col-span-6 xl:col-span-4">
          <div className="flex items-center gap-4">
            <ArcGauge score={dq.score} color={EMERALD} />
            <div className="flex-1 space-y-1.5">
              <p className="text-[10px] uppercase tracking-widest text-slate-500">Checks passing</p>
              <p className="mono text-[15px] text-slate-100">{dq.successful}/{dq.evaluated}</p>
              <ul className="space-y-1">
                {dq.checks.slice(0, 4).map((c) => (
                  <li key={c.name} className="flex items-center justify-between gap-2">
                    <span className="truncate text-[10.5px] text-slate-400">{c.name}</span>
                    <span className="mono text-[9.5px]"
                      style={{ color: c.status === "pass" ? EMERALD : GOLD }}>
                      {c.score.toFixed(3)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Panel>

        <Panel title="Latest claims" accent={CYAN} className="col-span-12 xl:col-span-7">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="mono text-[9px] uppercase tracking-widest text-slate-500">
                  <th className="pb-2 pr-3 font-normal">claim</th>
                  <th className="pb-2 pr-3 font-normal">county</th>
                  <th className="pb-2 pr-3 font-normal">lob</th>
                  <th className="pb-2 pr-3 text-right font-normal">amount</th>
                  <th className="pb-2 pr-3 font-normal">status</th>
                  <th className="pb-2 text-right font-normal">fraud</th>
                </tr>
              </thead>
              <tbody>
                {claims.map((c) => (
                  <tr key={c.claim_id} className="border-t border-slate-800/70">
                    <td className="mono py-1.5 pr-3 text-[10.5px] text-slate-300">{c.claim_id}</td>
                    <td className="py-1.5 pr-3 text-[10.5px] text-slate-400">{c.county}</td>
                    <td className="py-1.5 pr-3 text-[10.5px] text-slate-400">{c.lob}</td>
                    <td className="mono py-1.5 pr-3 text-right text-[10.5px] text-slate-200">
                      {kes(c.amount_kes, 0)}
                    </td>
                    <td className="py-1.5 pr-3">
                      <span className="mono rounded px-1.5 py-0.5 text-[9px] uppercase tracking-wider"
                        style={{ color: STATUS_TONE[c.status], background: `${STATUS_TONE[c.status]}1a` }}>
                        {c.status}
                      </span>
                    </td>
                    <td className="mono py-1.5 text-right text-[10.5px]"
                      style={{ color: c.fraud_score > 0.75 ? ROSE : c.fraud_score > 0.4 ? GOLD : "#94a3b8" }}>
                      {c.fraud_score.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel id="fraud" title="Claims and fraud intensity" accent={ROSE} className="col-span-12 xl:col-span-5">
          <div className="mb-2 flex items-center gap-4">
            <Legend color={CYAN} label="Claims" />
            <Legend color={ROSE} label="Flagged" />
          </div>
          <Columns
            labels={intensity.map((i) => i.month.slice(0, 1))}
            primary={intensity.map((i) => i.claims)}
            secondary={intensity.map((i) => i.flagged)}
            primaryColor={CYAN}
            secondaryColor={ROSE}
          />
        </Panel>

        <Panel title="Executive narrative" accent={GOLD} className="col-span-12 xl:col-span-8">
          <div className="grid gap-3 md:grid-cols-3">
            {narrative.map((n, i) => (
              <article key={n.title} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                <p className="mono text-[9px] uppercase tracking-widest text-goldaccent">
                  note {String(i + 1).padStart(2, "0")}
                </p>
                <h3 className="mt-1.5 text-[12px] font-medium text-slate-100">{n.title}</h3>
                <p className="mt-1.5 text-[11px] leading-relaxed text-slate-400">{n.body}</p>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Live event ticker" accent={CYAN} className="col-span-12 xl:col-span-4">
          <LiveEventTicker events={events} />
        </Panel>
      </div>

      <footer className="mono mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-3 text-[9.5px] uppercase tracking-widest text-slate-600">
        <span>Insurelake {"\u00B7"} executive control centre</span>
        <span>bronze {"\u2192"} silver {"\u2192"} gold {"\u00B7"} 47 counties {"\u00B7"} data as of 28 Dec 2024</span>
      </footer>
    </main>
  );
}
