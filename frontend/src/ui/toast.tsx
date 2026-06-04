import { useEffect, useMemo, useState } from "react";

import { generateId } from "../utils/id";

type Toast = { id: string; title: string; detail?: string };

let pushToast: ((t: Toast) => void) | null = null;

export function toast(title: string, detail?: string) {
  pushToast?.({ id: generateId(), title, detail });
}

export function ToastHost() {
  const [items, setItems] = useState<Toast[]>([]);

  const api = useMemo(() => {
    return (t: Toast) => setItems((prev) => [t, ...prev].slice(0, 3));
  }, []);

  useEffect(() => {
    pushToast = api;
    return () => {
      pushToast = null;
    };
  }, [api]);

  useEffect(() => {
    if (items.length === 0) return;
    const id = setTimeout(() => setItems((prev) => prev.slice(0, -1)), 3500);
    return () => clearTimeout(id);
  }, [items]);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-[340px] flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className="rounded-xl border border-surface-subtle bg-surface p-4 shadow-soft"
        >
          <div className="text-sm font-semibold text-ink">{t.title}</div>
          {t.detail ? <div className="mt-1 text-xs text-ink-muted">{t.detail}</div> : null}
        </div>
      ))}
    </div>
  );
}

