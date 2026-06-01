import { formatISO, startOfMonth, endOfMonth, subDays } from "date-fns";

export type PeriodPreset =
  | "today"
  | "yesterday"
  | "7d"
  | "14d"
  | "30d"
  | "current_month"
  | "previous_month"
  | "custom";

export type DateRange = { start: string; end: string };

export type PeriodSelection = {
  preset: PeriodPreset;
  range: DateRange;
  compareEnabled: boolean;
  comparePreset: "previous_period" | "custom";
  compareRange?: DateRange;
};

const KEY = "ma.periodSelection.v1";

function isoDay(d: Date) {
  return formatISO(d, { representation: "date" });
}

export function computePreset(preset: PeriodPreset, now = new Date()): DateRange {
  if (preset === "today") return { start: isoDay(now), end: isoDay(now) };
  if (preset === "yesterday") {
    const d = subDays(now, 1);
    return { start: isoDay(d), end: isoDay(d) };
  }
  if (preset === "7d") return { start: isoDay(subDays(now, 6)), end: isoDay(now) };
  if (preset === "14d") return { start: isoDay(subDays(now, 13)), end: isoDay(now) };
  if (preset === "30d") return { start: isoDay(subDays(now, 29)), end: isoDay(now) };
  if (preset === "current_month") return { start: isoDay(startOfMonth(now)), end: isoDay(endOfMonth(now)) };
  if (preset === "previous_month") {
    const prev = subDays(startOfMonth(now), 1);
    return { start: isoDay(startOfMonth(prev)), end: isoDay(endOfMonth(prev)) };
  }
  // custom must be supplied by caller
  return { start: isoDay(subDays(now, 13)), end: isoDay(now) };
}

export function previousPeriod(range: DateRange): DateRange {
  const start = new Date(range.start);
  const end = new Date(range.end);
  const days = Math.round((end.getTime() - start.getTime()) / (24 * 3600 * 1000)) + 1;
  const prevEnd = subDays(start, 1);
  const prevStart = subDays(prevEnd, days - 1);
  return { start: isoDay(prevStart), end: isoDay(prevEnd) };
}

export function loadPeriodSelection(): PeriodSelection {
  const raw = localStorage.getItem(KEY);
  if (!raw) {
    const range = computePreset("14d");
    return { preset: "14d", range, compareEnabled: false, comparePreset: "previous_period" };
  }
  try {
    return JSON.parse(raw) as PeriodSelection;
  } catch {
    const range = computePreset("14d");
    return { preset: "14d", range, compareEnabled: false, comparePreset: "previous_period" };
  }
}

export function savePeriodSelection(sel: PeriodSelection) {
  localStorage.setItem(KEY, JSON.stringify(sel));
}

