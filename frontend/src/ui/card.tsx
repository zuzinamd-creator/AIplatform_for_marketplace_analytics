import React from "react";

import { cx } from "./cx";

export function Card(props: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={cx("rounded-xl border border-slate-800/70 bg-slate-900/40", props.className)}
    />
  );
}

