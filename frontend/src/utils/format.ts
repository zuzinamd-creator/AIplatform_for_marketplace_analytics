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

/**
 * Compact chart labels (display-only).
 * Examples: 1250 → "1.3 тыс.", 1_250_000 → "1.25 млн."
 */
export function formatCompactRub(value: unknown): string {
  const n = parseNumeric(value);
  if (n === null) return "";
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";
  if (abs < 1000) {
    const rounded = Math.round(abs * 100) / 100;
    const base =
      Number.isInteger(rounded) || Math.abs(rounded - Math.round(rounded)) < 1e-9
        ? String(Math.round(rounded))
        : rounded.toFixed(2).replace(/\.?0+$/, "");
    return `${sign}${base}`;
  }
  if (abs < 1_000_000) {
    const v = Math.round((abs / 1000) * 10) / 10;
    const text = Number.isInteger(v) ? String(v) : v.toFixed(1);
    return `${sign}${text} тыс.`;
  }
  const v = Math.round((abs / 1_000_000) * 100) / 100;
  const text = Number.isInteger(v) ? String(v) : String(v);
  return `${sign}${text} млн.`;
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
