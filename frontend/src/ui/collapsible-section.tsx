import React from "react";

import { cx } from "./cx";

type Props = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
  actions?: React.ReactNode;
};

/** Progressive disclosure via native &lt;details&gt; — no extra state or data logic. */
export function CollapsibleSection({
  title,
  subtitle,
  children,
  defaultOpen = false,
  className,
  actions,
}: Props) {
  return (
    <details className={cx("disclosure-panel group", className)} open={defaultOpen || undefined}>
      <summary className="disclosure-summary">
        <span className="min-w-0 flex-1">
          <span className="block">{title}</span>
          {subtitle ? <span className="mt-0.5 block text-xs font-normal text-ink-muted">{subtitle}</span> : null}
        </span>
        {actions ? (
          <span
            className="shrink-0"
            onClick={(e) => e.preventDefault()}
            onKeyDown={(e) => e.stopPropagation()}
          >
            {actions}
          </span>
        ) : null}
      </summary>
      <div className="disclosure-body">{children}</div>
    </details>
  );
}
