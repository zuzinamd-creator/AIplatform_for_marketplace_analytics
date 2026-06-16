import type { ReportResponse } from "../../state/types-reports";
import { reportPeriodKey } from "./report-period-sort";

export type PeriodGranularity = "month" | "week";

export type MissingPeriodGap = {
  id: string;
  marketplace: string;
  label: string;
};

export type ReportTableRow<T extends ReportResponse = ReportResponse> =
  | { kind: "report"; report: T }
  | { kind: "gap"; gap: MissingPeriodGap };

function parseIsoDate(iso?: string | null): number | null {
  if (!iso) return null;
  const d = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return null;
  const ms = Date.parse(`${d}T00:00:00.000Z`);
  return Number.isNaN(ms) ? null : ms;
}

function utcParts(iso: string): { y: number; m: number; d: number } | null {
  const d = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return null;
  const [y, m, day] = d.split("-").map(Number);
  return { y, m, d: day };
}

function lastDayOfMonth(y: number, m: number): number {
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}

function daysInclusive(start: string, end: string): number | null {
  const s = parseIsoDate(start);
  const e = parseIsoDate(end);
  if (s == null || e == null || e < s) return null;
  return Math.round((e - s) / 86_400_000) + 1;
}

export function detectPeriodGranularity(
  start?: string | null,
  end?: string | null,
): PeriodGranularity | null {
  if (!start || !end) return null;
  const s = start.slice(0, 10);
  const e = end.slice(0, 10);
  const sp = utcParts(s);
  const ep = utcParts(e);
  if (!sp || !ep) return null;
  if (sp.d === 1 && sp.y === ep.y && sp.m === ep.m && ep.d === lastDayOfMonth(sp.y, sp.m)) {
    return "month";
  }
  if (daysInclusive(s, e) === 7) return "week";
  return null;
}

function monthKey(start: string, end: string): string | null {
  if (detectPeriodGranularity(start, end) !== "month") return null;
  return start.slice(0, 7);
}

function weekStartKey(start: string, end: string): string | null {
  if (detectPeriodGranularity(start, end) !== "week") return null;
  return start.slice(0, 10);
}

function addMonthsYm(ym: string, delta: number): string {
  let [y, m] = ym.split("-").map(Number);
  m += delta;
  while (m > 12) {
    m -= 12;
    y += 1;
  }
  while (m < 1) {
    m += 12;
    y -= 1;
  }
  return `${y}-${String(m).padStart(2, "0")}`;
}

function addDaysIso(iso: string, delta: number): string {
  const ms = parseIsoDate(iso);
  if (ms == null) return iso;
  const d = new Date(ms + delta * 86_400_000);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fmtGapWeekLabel(weekStart: string): string {
  const weekEnd = addDaysIso(weekStart, 6);
  const fmt = (iso: string) => {
    const [y, m, d] = iso.split("-");
    return `${d}.${m}.${y}`;
  };
  return `${fmt(weekStart)} — ${fmt(weekEnd)}`;
}

function findMissingMonths(
  earlier: Pick<ReportResponse, "period_start" | "period_end">,
  later: Pick<ReportResponse, "period_start" | "period_end">,
): string[] {
  const start = earlier.period_start?.slice(0, 10);
  const endEarlier = earlier.period_end?.slice(0, 10);
  const startLater = later.period_start?.slice(0, 10);
  const endLater = later.period_end?.slice(0, 10);
  if (!start || !endEarlier || !startLater || !endLater) return [];

  const m1 = monthKey(start, endEarlier);
  const m2 = monthKey(startLater, endLater);
  if (!m1 || !m2 || m1 >= m2) return [];

  const gaps: string[] = [];
  let cursor = addMonthsYm(m1, 1);
  while (cursor < m2) {
    gaps.push(cursor);
    cursor = addMonthsYm(cursor, 1);
  }
  return gaps;
}

function findMissingWeeks(
  earlier: Pick<ReportResponse, "period_start" | "period_end">,
  later: Pick<ReportResponse, "period_start" | "period_end">,
): string[] {
  const start = earlier.period_start?.slice(0, 10);
  const endEarlier = earlier.period_end?.slice(0, 10);
  const startLater = later.period_start?.slice(0, 10);
  const endLater = later.period_end?.slice(0, 10);
  if (!start || !endEarlier || !startLater || !endLater) return [];

  const w1 = weekStartKey(start, endEarlier);
  const w2 = weekStartKey(startLater, endLater);
  if (!w1 || !w2 || w1 >= w2) return [];

  const gaps: string[] = [];
  let cursor = addDaysIso(w1, 7);
  while (cursor < w2) {
    gaps.push(fmtGapWeekLabel(cursor));
    cursor = addDaysIso(cursor, 7);
  }
  return gaps;
}

export function findMissingPeriodsBetween(
  a: Pick<ReportResponse, "period_start" | "period_end">,
  b: Pick<ReportResponse, "period_start" | "period_end">,
): string[] {
  const keyA = reportPeriodKey(a);
  const keyB = reportPeriodKey(b);
  if (!keyA || !keyB) return [];

  const earlier = keyA[0] <= keyB[0] ? a : b;
  const later = keyA[0] <= keyB[0] ? b : a;

  const granEarlier = detectPeriodGranularity(earlier.period_start, earlier.period_end);
  const granLater = detectPeriodGranularity(later.period_start, later.period_end);
  if (!granEarlier || granEarlier !== granLater) return [];

  if (granEarlier === "month") return findMissingMonths(earlier, later);
  return findMissingWeeks(earlier, later);
}

export function buildReportTableRows<T extends ReportResponse>(reports: T[]): ReportTableRow<T>[] {
  const rows: ReportTableRow<T>[] = [];

  for (let i = 0; i < reports.length; i++) {
    const current = reports[i];
    rows.push({ kind: "report", report: current });

    const next = reports[i + 1];
    if (!next || current.marketplace !== next.marketplace) continue;

    const gaps = findMissingPeriodsBetween(current, next);
    for (const label of gaps) {
      rows.push({
        kind: "gap",
        gap: {
          id: `gap-${current.id}-${next.id}-${label}`,
          marketplace: current.marketplace,
          label,
        },
      });
    }
  }

  return rows;
}
