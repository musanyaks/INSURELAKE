import Link from "next/link";

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function Panel({
  id,
  title,
  accent,
  badge,
  link,
  className,
  bodyClassName,
  children,
}: {
  id?: string;
  title: string;
  accent: string;
  badge?: string;
  link?: { label: string; href: string };
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className={cx(
        "relative flex flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur",
        className,
      )}
    >
      <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: accent }} />
      <header className="flex items-center justify-between gap-3 border-b border-slate-800/70 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: accent }} />
          <h2 className="truncate text-[12.5px] font-medium tracking-wide text-slate-200">
            {title}
          </h2>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {badge ? (
            <span className="mono rounded border border-slate-700 px-1.5 py-0.5 text-[9.5px] uppercase tracking-widest text-slate-400">
              {badge}
            </span>
          ) : null}
          {link ? (
            <Link
              href={link.href}
              className="mono text-[9.5px] uppercase tracking-widest text-slate-500 transition hover:text-cyan-300"
            >
              {link.label}
            </Link>
          ) : null}
        </div>
      </header>
      <div className={cx("flex-1 p-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function Kpi({
  label,
  value,
  sub,
  tone,
  delta,
  deltaSuffix = "%",
  Icon,
}: {
  label: string;
  value: string;
  sub: string;
  tone: string;
  delta?: number;
  deltaSuffix?: string;
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number; color?: string }>;
}) {
  const up = (delta ?? 0) >= 0;
  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/40 p-3.5">
      <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: tone }} />
      <div className="flex items-start justify-between gap-2">
        <div
          className="flex h-[26px] w-[26px] items-center justify-center rounded-md"
          style={{ background: `${tone}1f`, border: `1px solid ${tone}40` }}
        >
          <Icon size={14} strokeWidth={1.8} color={tone} />
        </div>
        {typeof delta === "number" ? (
          <span className="mono text-[10px]" style={{ color: up ? "#34d399" : "#f43f5e" }}>
            {up ? "\u25B2" : "\u25BC"} {Math.abs(delta).toFixed(1)}
            {deltaSuffix}
          </span>
        ) : null}
      </div>
      <p className="mt-2.5 text-[10px] uppercase tracking-widest text-slate-500">{label}</p>
      <p className="mono mt-1 text-[19px] leading-none text-slate-100">{value}</p>
      <p className="mt-1.5 text-[10.5px] text-slate-500">{sub}</p>
    </div>
  );
}

export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="mono rounded-full border border-slate-700/80 bg-slate-900/60 px-2.5 py-1 text-[10px] uppercase tracking-widest text-slate-400">
      {children}
    </span>
  );
}

export function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-[10.5px] text-slate-400">
      <span className="h-2 w-2 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}
