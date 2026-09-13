/** Display formatters. Numbers in tables are right-aligned and monospaced. */

const num = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const fmtPrice = (v: number | null | undefined) => (v == null ? "—" : num.format(v));

export const fmtPct = (v: number | null | undefined) =>
  v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;

export function fmtCompact(v: number | null | undefined): string {
  if (v == null) return "—";
  const abs = Math.abs(v);
  if (abs >= 1e7) return `${(v / 1e7).toFixed(2)}Cr`;
  if (abs >= 1e5) return `${(v / 1e5).toFixed(2)}L`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(0);
}

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
