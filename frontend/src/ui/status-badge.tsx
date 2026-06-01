import React from "react";

import { cx } from "./cx";

export function StatusBadge(props: { tone?: "ok" | "warn" | "bad" | "info"; children: React.ReactNode }) {
  const tone = props.tone ?? "info";
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        tone === "ok" && "bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-500/20",
        tone === "warn" && "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/20",
        tone === "bad" && "bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/20",
        tone === "info" && "bg-sky-500/15 text-sky-200 ring-1 ring-sky-500/20",
      )}
    >
      {props.children}
    </span>
  );
}

