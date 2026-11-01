import { compact } from "@/lib/format";

type Series = {
  key: string;
  label: string;
  color: string;
  values: number[];
};

export function AreaTrend({
  labels,
  series,
  height = 200,
}: {
  labels: string[];
  series: Series[];
  height?: number;
}) {
  const W = 760;
  const H = height;
  const padT = 14;
  const padB = 24;
  const padL = 40;
  const padR = 10;
  const iw = W - padL - padR;
  const ih = H - padT - padB;
  const all = series.flatMap((s) => s.values);
  const max = Math.max(...all) * 1.15 || 1;

  const x = (i: number) => padL + (labels.length <= 1 ? 0 : (i / (labels.length - 1)) * iw);
  const y = (v: number) => padT + ih - (v / max) * ih;

  const line = (values: number[]) =>
    values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  const area = (values: number[]) =>
    `${line(values)} L${x(values.length - 1).toFixed(1)},${padT + ih} L${padL},${padT + ih} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" preserveAspectRatio="none">
      {[0, 0.5, 1].map((t) => (
        <line
          key={t}
          x1={padL}
          x2={W - padR}
          y1={padT + ih * t}
          y2={padT + ih * t}
          stroke="#1e293b"
          strokeDasharray="3 4"
          strokeWidth="1"
        />
      ))}
      {[0, 0.5, 1].map((t) => (
        <text
          key={`y${t}`}
          x={padL - 6}
          y={padT + ih * t + 3}
          textAnchor="end"
          fontSize="9"
          fill="#64748b"
          fontFamily="monospace"
        >
          {compact(max * (1 - t))}
        </text>
      ))}
      {series.map((s) => (
        <g key={s.key}>
          <path d={area(s.values)} fill={s.color} opacity="0.10" />
          <path d={line(s.values)} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" />
          {s.values.map((v, i) => (
            <circle key={i} cx={x(i)} cy={y(v)} r="2" fill={s.color} />
          ))}
        </g>
      ))}
      {labels.map((l, i) =>
        i % 2 === 0 ? (
          <text
            key={l}
            x={x(i)}
            y={H - 6}
            textAnchor="middle"
            fontSize="9"
            fill="#64748b"
            fontFamily="monospace"
          >
            {l}
          </text>
        ) : null,
      )}
    </svg>
  );
}

export function BarList({
  items,
  color,
  unit,
}: {
  items: { label: string; value: number; note?: string }[];
  color: string;
  unit?: string;
}) {
  const max = Math.max(...items.map((i) => i.value)) || 1;
  return (
    <ul className="space-y-2.5">
      {items.map((item) => (
        <li key={item.label}>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[11px] text-slate-300">{item.label}</span>
            <span className="mono text-[10.5px] text-slate-400">
              {item.note ?? `${item.value}${unit ?? ""}`}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full"
              style={{ width: `${Math.max(3, (item.value / max) * 100)}%`, background: color }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function Donut({
  items,
  palette,
  centerLabel,
  centerValue,
}: {
  items: { label: string; share: number }[];
  palette: string[];
  centerLabel: string;
  centerValue: string;
}) {
  let acc = 0;
  const stops: string[] = [];
  items.forEach((item, i) => {
    const start = acc;
    acc += item.share;
    stops.push(`${palette[i % palette.length]} ${start * 360}deg ${acc * 360}deg`);
  });

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-[112px] w-[112px] shrink-0">
        <div
          className="h-full w-full rounded-full"
          style={{ background: `conic-gradient(${stops.join(",")})` }}
        />
        <div className="absolute inset-[16px] flex flex-col items-center justify-center rounded-full bg-ink">
          <span className="mono text-[13px] text-slate-100">{centerValue}</span>
          <span className="text-[8.5px] uppercase tracking-widest text-slate-500">
            {centerLabel}
          </span>
        </div>
      </div>
      <ul className="flex-1 space-y-1.5">
        {items.map((item, i) => (
          <li key={item.label} className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-[11px] text-slate-300">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ background: palette[i % palette.length] }}
              />
              {item.label}
            </span>
            <span className="mono text-[10.5px] text-slate-400">
              {(item.share * 100).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Columns({
  labels,
  primary,
  secondary,
  primaryColor,
  secondaryColor,
  height = 170,
}: {
  labels: string[];
  primary: number[];
  secondary: number[];
  primaryColor: string;
  secondaryColor: string;
  height?: number;
}) {
  const max = Math.max(...primary, ...secondary) || 1;
  const ih = height - 22;
  return (
    <div className="flex items-end gap-1.5" style={{ height }}>
      {labels.map((label, i) => (
        <div key={`${label}-${i}`} className="flex flex-1 flex-col items-center justify-end gap-1">
          <div className="flex w-full items-end justify-center gap-[2px]" style={{ height: ih }}>
            <div
              className="w-1/2 rounded-t-sm"
              style={{
                height: `${Math.max(2, (primary[i] / max) * 100)}%`,
                background: primaryColor,
                opacity: 0.85,
              }}
            />
            <div
              className="w-1/2 rounded-t-sm"
              style={{
                height: `${Math.max(2, (secondary[i] / max) * 100)}%`,
                background: secondaryColor,
                opacity: 0.9,
              }}
            />
          </div>
          <span className="mono text-[8.5px] text-slate-500">{label}</span>
        </div>
      ))}
    </div>
  );
}

export function ArcGauge({ score, color }: { score: number; color: string }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, score));
  return (
    <div className="relative mx-auto h-[132px] w-[132px]">
      <svg viewBox="0 0 132 132" className="h-full w-full -rotate-90">
        <circle cx="66" cy="66" r={r} fill="none" stroke="#1e293b" strokeWidth="9" />
        <circle
          cx="66"
          cy="66"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${(c * clamped).toFixed(2)} ${c.toFixed(2)}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="mono text-[24px] leading-none text-slate-100">
          {(clamped * 100).toFixed(1)}
        </span>
        <span className="mt-1 text-[8.5px] uppercase tracking-widest text-slate-500">trust</span>
      </div>
    </div>
  );
}

export function HBar({
  items,
  color,
  formatValue,
}: {
  items: { label: string; value: number; note?: string }[];
  color: string;
  formatValue: (v: number) => string;
}) {
  const max = Math.max(...items.map((i) => i.value)) || 1;
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.label}>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-[11px] text-slate-300">{item.label}</span>
            <span className="mono text-[10.5px] text-slate-400">{formatValue(item.value)}</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full"
              style={{ width: `${Math.max(4, (item.value / max) * 100)}%`, background: color }}
            />
          </div>
          {item.note ? <p className="mt-1 text-[9.5px] text-slate-500">{item.note}</p> : null}
        </li>
      ))}
    </ul>
  );
}
