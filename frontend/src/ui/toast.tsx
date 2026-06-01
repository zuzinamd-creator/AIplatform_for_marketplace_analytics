import { useEffect, useMemo, useState } from "react";

type Toast = { id: string; title: string; detail?: string };

let pushToast: ((t: Toast) => void) | null = null;

export function toast(title: string, detail?: string) {
  pushToast?.({ id: crypto.randomUUID(), title, detail });
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
          className="rounded-xl border border-slate-800/70 bg-slate-950/85 p-3 shadow-soft backdrop-blur"
        >
          <div className="text-sm font-semibold">{t.title}</div>
          {t.detail ? <div className="mt-1 text-xs text-slate-300">{t.detail}</div> : null}
        </div>
      ))}
    </div>
  );
}

