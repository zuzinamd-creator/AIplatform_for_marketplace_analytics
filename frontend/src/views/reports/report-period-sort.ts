import type { ReportResponse } from "../../state/types-reports";

export type PeriodSortOrder = "asc" | "desc";

function parseIsoDate(iso?: string | null): number | null {
  if (!iso) return null;
  const d = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return null;
  const ms = Date.parse(`${d}T00:00:00.000Z`);
  return Number.isNaN(ms) ? null : ms;
}

/** Comparable period key from report fields (not display string). */
export function reportPeriodKey(report: Pick<ReportResponse, "period_start" | "period_end">): [number, number] | null {
  const startMs = parseIsoDate(report.period_start);
  const endMs = parseIsoDate(report.period_end) ?? startMs;
  if (startMs == null) return null;
  return [startMs, endMs ?? startMs];
}

export function compareReportPeriod(
  a: Pick<ReportResponse, "period_start" | "period_end">,
  b: Pick<ReportResponse, "period_start" | "period_end">,
  order: PeriodSortOrder,
): number {
  const ka = reportPeriodKey(a);
  const kb = reportPeriodKey(b);
  if (ka == null && kb == null) return 0;
  if (ka == null) return 1;
  if (kb == null) return -1;
  const cmp = ka[0] !== kb[0] ? ka[0] - kb[0] : ka[1] - kb[1];
  return order === "asc" ? cmp : -cmp;
}

export function sortReportsByPeriod<T extends Pick<ReportResponse, "period_start" | "period_end">>(
  rows: T[],
  order: PeriodSortOrder,
): T[] {
  return [...rows].sort((a, b) => compareReportPeriod(a, b, order));
}
