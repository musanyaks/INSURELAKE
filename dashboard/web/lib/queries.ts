const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function fetchJson<T>(path: string): Promise<T | null> {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1200),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export type Summary = {
  earned_premium_kes: number;
  incurred_claims_kes: number;
  loss_ratio: number;
  fraud_exposure_kes: number;
  ibnr_kes: number;
  retention_rate: number;
  deltas: {
    premium: number;
    claims: number;
    loss_ratio_pp: number;
    fraud: number;
    ibnr: number;
    retention_pp: number;
  };
};

export type TrendPoint = { month: string; premium: number; claims: number };
export type FraudLevel = { level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"; count: number };
export type CountyRow = { county: string; exposure_kes: number; claims: number; risk: number };
export type LobRow = { lob: string; premium_kes: number; share: number };
export type IbnrRow = { method: string; ibnr_kes: number; se_kes: number };
export type PaymentRow = { channel: string; amount_kes: number; share: number };
export type LayerRow = {
  layer: "bronze" | "silver" | "gold";
  rows: number;
  size_gb: number;
  tables: number;
};
export type DqCheck = { name: string; status: "pass" | "warn" | "fail"; score: number };
export type DqReport = {
  score: number;
  evaluated: number;
  successful: number;
  checks: DqCheck[];
};
export type ClaimRow = {
  claim_id: string;
  policy_id: string;
  county: string;
  lob: string;
  amount_kes: number;
  status: "OPEN" | "REVIEW" | "SETTLED" | "DECLINED";
  fraud_score: number;
  filed_at: string;
};
export type IntensityPoint = { month: string; claims: number; flagged: number };
export type NarrativeItem = { title: string; body: string };
export type EventItem = {
  id: string;
  ts: string;
  kind: string;
  severity: "info" | "warn" | "crit";
  message: string;
};

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

const COUNTIES = [
  "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta", "Garissa",
  "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka Nithi", "Embu",
  "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga", "Muranga",
  "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia", "Uasin Gishu",
  "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru", "Narok", "Kajiado",
  "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma", "Busia", "Siaya", "Kisumu",
  "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi",
];

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const LOBS = ["Motor", "Health", "Life", "Property", "Marine", "Agriculture", "Liability"];

const SUMMARY: Summary = {
  earned_premium_kes: 4_820_000_000,
  incurred_claims_kes: 3_110_000_000,
  loss_ratio: 0.645,
  fraud_exposure_kes: 214_000_000,
  ibnr_kes: 388_000_000,
  retention_rate: 0.784,
  deltas: {
    premium: 12.4,
    claims: 8.1,
    loss_ratio_pp: -2.6,
    fraud: -5.2,
    ibnr: 3.4,
    retention_pp: 1.1,
  },
};

const TREND: TrendPoint[] = MONTHS.map((month, i) => ({
  month,
  premium: 280_000_000 + i * 18_400_000 + hash(`p${month}`) * 12_000_000,
  claims: 190_000_000 + i * 10_900_000 + hash(`c${month}`) * 9_000_000,
}));

const FRAUD: FraudLevel[] = [
  { level: "CRITICAL", count: 128 },
  { level: "HIGH", count: 412 },
  { level: "MEDIUM", count: 1_184 },
  { level: "LOW", count: 4_902 },
];

const PAYMENTS: PaymentRow[] = [
  { channel: "M-PESA", amount_kes: 1_920_000_000, share: 0.62 },
  { channel: "Bank transfer", amount_kes: 744_000_000, share: 0.24 },
  { channel: "Card", amount_kes: 279_000_000, share: 0.09 },
  { channel: "Cheque", amount_kes: 155_000_000, share: 0.05 },
];

const LAYERS: LayerRow[] = [
  { layer: "bronze", rows: 12_840_000, size_gb: 41.2, tables: 8 },
  { layer: "silver", rows: 11_260_000, size_gb: 28.7, tables: 11 },
  { layer: "gold", rows: 1_840_000, size_gb: 6.4, tables: 9 },
];

const DQ: DqReport = {
  score: 0.964,
  evaluated: 9,
  successful: 8,
  checks: [
    { name: "claims_completeness", status: "pass", score: 0.998 },
    { name: "customers_completeness", status: "pass", score: 1.0 },
    { name: "payments_validity", status: "pass", score: 0.991 },
    { name: "duplicate_records", status: "warn", score: 0.874 },
    { name: "policy_orphans", status: "pass", score: 0.996 },
    { name: "county_referential", status: "pass", score: 1.0 },
  ],
};

const CLAIM_STATUS: ClaimRow["status"][] = ["OPEN", "REVIEW", "SETTLED", "SETTLED", "DECLINED"];

const CLAIMS: ClaimRow[] = Array.from({ length: 12 }, (_, i) => {
  const county = COUNTIES[(i * 7 + 3) % COUNTIES.length];
  const lob = LOBS[(i * 3) % LOBS.length];
  const h = hash(`claim-${i}`);
  const day = 2 + i * 2;
  return {
    claim_id: `CLM-2024-${String(48120 + i * 37).padStart(5, "0")}`,
    policy_id: `POL-${String(90210 + i * 11)}`,
    county,
    lob,
    amount_kes: Math.round((48_000 + h * 1_820_000) / 100) * 100,
    status: CLAIM_STATUS[i % CLAIM_STATUS.length],
    fraud_score: Math.round(h * 100) / 100,
    filed_at: `2024-12-${String(Math.min(day, 28)).padStart(2, "0")}T09:${String(
      10 + (i % 45),
    ).padStart(2, "0")}:00Z`,
  };
});

const EVENTS: EventItem[] = [
  { id: "e1", ts: "2024-12-28T10:14:02Z", kind: "fraud.score", severity: "crit", message: "CLM-2024-48539 scored 0.94 - motor, Nairobi" },
  { id: "e2", ts: "2024-12-28T10:13:41Z", kind: "silver.claims", severity: "info", message: "micro-batch committed 1,284 rows to silver.claims" },
  { id: "e3", ts: "2024-12-28T10:12:55Z", kind: "mpesa.settlement", severity: "info", message: "M-PESA settlement batch 4412 reconciled (KSh 18.4M)" },
  { id: "e4", ts: "2024-12-28T10:11:30Z", kind: "dq.check", severity: "warn", message: "duplicate_records 0.874 - below 0.95 target" },
  { id: "e5", ts: "2024-12-28T10:10:12Z", kind: "gold.refresh", severity: "info", message: "gold.fact_claims refreshed, 9 partitions" },
  { id: "e6", ts: "2024-12-28T10:09:48Z", kind: "fraud.score", severity: "warn", message: "Provider PRV-0391 velocity anomaly - 14 claims / 24h" },
  { id: "e7", ts: "2024-12-28T10:08:03Z", kind: "actuarial", severity: "info", message: "Chain ladder cohort 2024-Q3 IBNR recomputed" },
  { id: "e8", ts: "2024-12-28T10:07:19Z", kind: "kafka.commit", severity: "info", message: "topic insurance.claims - offset 1,842,901 committed" },
];

export async function executiveSummary(): Promise<Summary> {
  const live = await fetchJson<Partial<Summary>>("/executive/summary");
  if (!live) return SUMMARY;
  return {
    ...SUMMARY,
    ...live,
    deltas: { ...SUMMARY.deltas, ...(live.deltas ?? {}) },
  };
}

export async function premiumVsClaimsTrend(): Promise<TrendPoint[]> {
  return (await fetchJson<TrendPoint[]>("/executive/premium-vs-claims")) ?? TREND;
}

export async function fraudAlertDistribution(): Promise<FraudLevel[]> {
  return (await fetchJson<FraudLevel[]>("/fraud/distribution")) ?? FRAUD;
}

export async function countyRisk(): Promise<CountyRow[]> {
  const live = await fetchJson<CountyRow[]>("/geo/county-risk");
  if (live) return live;
  return COUNTIES.map((county) => {
    const h = hash(county);
    return {
      county,
      exposure_kes: 40_000_000 + h * 260_000_000,
      claims: Math.round(18 + h * 940),
      risk: 0.15 + h * 0.85,
    };
  }).sort((a, b) => b.exposure_kes - a.exposure_kes);
}

export async function lineOfBusinessMix(): Promise<LobRow[]> {
  const live = await fetchJson<LobRow[]>("/portfolio/lob-mix");
  if (live) return live;
  const weights = [0.34, 0.24, 0.14, 0.12, 0.07, 0.05, 0.04];
  return LOBS.map((lob, i) => ({
    lob,
    premium_kes: SUMMARY.earned_premium_kes * weights[i],
    share: weights[i],
  }));
}

export async function ibnrByMethod(): Promise<IbnrRow[]> {
  const live = await fetchJson<IbnrRow[]>("/actuarial/ibnr-by-method");
  if (live) return live;
  const base = SUMMARY.ibnr_kes;
  return [
    { method: "Chain Ladder", ibnr_kes: base, se_kes: base * 0.15 },
    { method: "Bornhuetter-Ferguson", ibnr_kes: base * 1.09, se_kes: base * 0.12 },
    { method: "Cape Cod", ibnr_kes: base * 0.93, se_kes: base * 0.17 },
  ];
}

export async function paymentsBreakdown(): Promise<PaymentRow[]> {
  return (await fetchJson<PaymentRow[]>("/payments/breakdown")) ?? PAYMENTS;
}

export async function layerCounts(): Promise<LayerRow[]> {
  return (await fetchJson<LayerRow[]>("/lakehouse/layers")) ?? LAYERS;
}

export async function dataQuality(): Promise<DqReport> {
  return (await fetchJson<DqReport>("/governance/quality")) ?? DQ;
}

export async function recentClaims(limit = 12): Promise<ClaimRow[]> {
  const live = await fetchJson<ClaimRow[]>(`/claims/recent?limit=${limit}`);
  return (live ?? CLAIMS).slice(0, limit);
}

export async function claimsAndFraudIntensity(): Promise<IntensityPoint[]> {
  const live = await fetchJson<IntensityPoint[]>("/claims/intensity");
  if (live) return live;
  return MONTHS.map((month) => ({
    month,
    claims: 620 + Math.round(hash(`i${month}`) * 380),
    flagged: 58 + Math.round(hash(`f${month}`) * 96),
  }));
}

export async function executiveNarrative(): Promise<NarrativeItem[]> {
  const live = await fetchJson<NarrativeItem[]>("/executive/narrative");
  if (live) return live;
  return [
    {
      title: "Premium growth outpaces claims",
      body:
        "Earned premium grew 12.4% year on year against 8.1% claims growth, pulling the loss ratio down 2.6 points to 64.5%. Motor and health carry 58% of the book and remain the two classes to watch.",
    },
    {
      title: "Fraud controls are biting",
      body:
        "Streaming XGBoost scoring flagged 128 critical alerts this cycle, down 5.2% on the prior period while volume rose. Estimated fraud exposure sits at KSh 214M, concentrated in Nairobi, Kiambu and Mombasa.",
    },
    {
      title: "Reserves remain adequate",
      body:
        "Chain ladder IBNR of KSh 388M is bracketed by Bornhuetter-Ferguson (KSh 423M) and Cape Cod (KSh 361M). The 15% Mack standard error keeps the central estimate inside the Board's risk appetite.",
    },
  ];
}

export async function liveEvents(): Promise<EventItem[]> {
  return (await fetchJson<EventItem[]>("/events/ticker")) ?? EVENTS;
}
