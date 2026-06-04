import React from "react";

import { Card } from "./card";
import { cx } from "./cx";

/** Semantic warning block — readable on light surfaces (no amber-on-white). */
export function WarnCallout(props: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <Card className={cx("border-semantic-warn/25 bg-semantic-warn-bg p-5", props.className)}>
      <div className="text-sm font-semibold text-semantic-warn">{props.title}</div>
      <div className="mt-3 text-sm leading-relaxed text-ink-secondary">{props.children}</div>
    </Card>
  );
}
