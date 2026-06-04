import React from "react";

import { cx } from "./cx";

export function StatusBadge(props: { tone?: "ok" | "warn" | "bad" | "info"; children: React.ReactNode }) {
  const tone = props.tone ?? "info";
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        tone === "ok" && "bg-semantic-success-bg text-semantic-success ring-1 ring-emerald-200",
        tone === "warn" && "bg-semantic-warn-bg text-semantic-warn ring-1 ring-amber-200",
        tone === "bad" && "bg-semantic-danger-bg text-semantic-danger ring-1 ring-red-200",
        tone === "info" && "bg-semantic-info-bg text-semantic-info ring-1 ring-sky-200",
      )}
    >
      {props.children}
    </span>
  );
}
