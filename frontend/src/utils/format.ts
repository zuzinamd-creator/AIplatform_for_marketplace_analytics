/** Display-only formatters — do not change API payloads or business calculations. */

export function parseNumeric(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const t = String(value).trim().replace(",", ".");
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

/** Generic number: up to 2 fractional digits (ru-RU). */
export function formatMetric(value: unknown, opts?: { suffix?: string }): string {
  const n = parseNumeric(value);
  if (n === null) return "—";
  const rounded = Math.round(n * 100) / 100;
  const base = rounded.toLocaleString("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  return base + (opts?.suffix ?? "");
}

export function formatRub(value: unknown): string {
  const n = parseNumeric(value);
  if (n === null) return "—";
  return formatMetric(n) + " ₽";
}

export function formatPct(value: unknown): string {
  const n = parseNumeric(value);
  if (n === null) return "—";
  return formatMetric(n) + " %";
}

export function formatUsd(value: unknown): string {
  const n = parseNumeric(value);
  if (n === null) return "—";
  return "$" + formatMetric(n);
}

/** Whole units (stock counts, queue depth) — no decimals. */
export function formatInteger(value: unknown): string {
  const n = parseNumeric(value);
  if (n === null) return "—";
  return Math.round(n).toLocaleString("ru-RU");
}

/** Recharts tooltip: [label, series name]. */
export function chartRubTooltip(value: unknown, name: string): [string, string] {
  return [formatRub(value), name];
}

export function chartPctTooltip(value: unknown, name: string): [string, string] {
  return [formatPct(value), name];
}

export function chartMetricTooltip(value: unknown, name: string): [string, string] {
  return [formatMetric(value), name];
}
