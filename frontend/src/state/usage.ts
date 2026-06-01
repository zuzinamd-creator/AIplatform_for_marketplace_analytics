export type UsageEvent = {
  at: string;
  action: string;
  meta?: Record<string, string>;
};

const KEY = "ma.usageEvents";
const MAX = 200;

export function trackUsage(action: string, meta?: Record<string, string>) {
  const raw = localStorage.getItem(KEY);
  const items: UsageEvent[] = raw ? (JSON.parse(raw) as UsageEvent[]) : [];
  items.unshift({ at: new Date().toISOString(), action, meta });
  localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX)));
}

export function loadUsage(): UsageEvent[] {
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as UsageEvent[];
  } catch {
    return [];
  }
}
