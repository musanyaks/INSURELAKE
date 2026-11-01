export function kes(n: number, digits = 2): string {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `KSh ${(n / 1e9).toFixed(digits)}B`;
  if (abs >= 1e6) return `KSh ${(n / 1e6).toFixed(digits)}M`;
  if (abs >= 1e3) return `KSh ${(n / 1e3).toFixed(1)}K`;
  return `KSh ${n.toFixed(0)}`;
}

export function kesM(n: number, digits = 0): string {
  return `${(n / 1e6).toFixed(digits)}M`;
}

export function count(n: number): string {
  return new Intl.NumberFormat("en-KE").format(Math.round(n));
}

export function compact(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return `${Math.round(n)}`;
}

export function pct(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`;
}

export function signed(n: number, digits = 1): string {
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}`;
}

export function shortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function shortTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
