import React from "react";

import { Card } from "./card";
import { cx } from "./cx";

type Props = {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  icon?: React.ReactNode;
  variant?: "hero" | "compact";
  className?: string;
};

export function KpiCard({ label, value, sub, icon, variant = "compact", className }: Props) {
  const isHero = variant === "hero";
  return (
    <Card
      className={cx(
        isHero ? "border-brand/20 bg-gradient-to-br from-brand-subtle/80 to-surface p-6 shadow-soft" : "p-5",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className={cx("font-medium text-ink-muted", isHero ? "text-sm" : "text-xs")}>{label}</div>
          <div
            className={cx(
              "mt-2 font-semibold tracking-tight text-ink",
              isHero ? "text-3xl md:text-4xl" : "text-xl",
            )}
          >
            {value}
          </div>
          {sub ? (
            <div className={cx("mt-2 leading-relaxed text-ink-muted", isHero ? "text-sm" : "text-xs")}>{sub}</div>
          ) : null}
        </div>
        {icon ? (
          <div
            className={cx(
              "shrink-0 rounded-xl text-ink-secondary",
              isHero ? "bg-surface p-3 shadow-sm ring-1 ring-surface-subtle" : "bg-surface-inset p-2.5 ring-1 ring-surface-subtle/80",
            )}
          >
            {icon}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
