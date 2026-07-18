import type { ReactNode } from "react";

/** Static title/aria hint next to a metric label (no fetch, no AI). */
export function MetricInfoHint({
  label,
  hint,
}: {
  label: ReactNode;
  hint: string;
}) {
  return (
    <span className="inline-flex items-center gap-1">
      {label}
      <span
        className="inline-flex h-3.5 w-3.5 shrink-0 cursor-help items-center justify-center rounded-full text-[9px] font-semibold text-ink-faint ring-1 ring-ink-faint/40"
        title={hint}
        aria-label={hint}
      >
        i
      </span>
    </span>
  );
}
