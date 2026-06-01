export type AppNotification = {
  id: string;
  title: string;
  detail?: string;
  tone: "info" | "warn" | "bad" | "ok";
  created_at: string;
  read: boolean;
  href?: string;
};

const KEY = "ma.notifications";
const MAX = 50;

export function loadNotifications(): AppNotification[] {
  const raw = localStorage.getItem(KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as AppNotification[];
  } catch {
    return [];
  }
}

function persist(items: AppNotification[]) {
  localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX)));
}

export function pushNotification(n: Omit<AppNotification, "id" | "created_at" | "read">) {
  const items = loadNotifications();
  const next: AppNotification = {
    ...n,
    id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
    read: false,
  };
  persist([next, ...items]);
  return next;
}

export function markRead(id: string) {
  const items = loadNotifications().map((n) => (n.id === id ? { ...n, read: true } : n));
  persist(items);
}

export function markAllRead() {
  persist(loadNotifications().map((n) => ({ ...n, read: true })));
}

export function unreadCount() {
  return loadNotifications().filter((n) => !n.read).length;
}
