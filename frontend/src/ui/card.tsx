import React from "react";

import { cx } from "./cx";

export function Card(props: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={cx(
        "rounded-2xl border border-surface-subtle/90 bg-surface shadow-card",
        props.className,
      )}
    />
  );
}
