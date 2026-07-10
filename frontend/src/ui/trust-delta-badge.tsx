import { BarChart3, TrendingDown, TrendingUp } from "lucide-react";

import {
  formatDeltaWithTrust,
  guardPeriodCompareDeltaMargin,
  guardPeriodCompareDeltaProfit,
  type ProfitTrustLevel,
} from "../state/profit-trust";
import { formatInteger, parseNumeric } from "../utils/format";
import { StatusBadge } from "./status-badge";

type Props = {
  value: unknown;
  format?: "rub" | "pct" | "int";
  trust?: ProfitTrustLevel;
  /** When set, apply period-compare profit null-coercion guard. */
  aProfit?: unknown;
  bProfit?: unknown;
  aMargin?: unknown;
  bMargin?: unknown;
};

function DeltaTone(props: {
  trust?: ProfitTrustLevel;
  format?: "rub" | "pct" | "int";
  n: number | null;
}): "ok" | "warn" | "bad" | "info" {
  if (props.n === null) return "info";
  if (props.trust === "partial" && (props.format === "rub" || props.format === "pct")) {
    return "warn";
  }
  if (props.n > 0) return "ok";
  if (props.n < 0) return "bad";
  return "info";
}

export function TrustDeltaBadge({
  value,
  format = "rub",
  trust,
  aProfit,
  bProfit,
  aMargin,
  bMargin,
}: Props) {
  let effectiveValue = value;

  if (trust && format === "rub" && (aProfit !== undefined || bProfit !== undefined)) {
    effectiveValue = guardPeriodCompareDeltaProfit(value, trust, aProfit, bProfit);
  }
  if (trust && format === "pct" && (aMargin !== undefined || bMargin !== undefined)) {
    effectiveValue = guardPeriodCompareDeltaMargin(value, trust, aMargin, bMargin);
  }

  if (trust && (format === "rub" || format === "pct")) {
    const formatted = formatDeltaWithTrust(effectiveValue, trust, format);
    if (formatted === "—" || formatted === "н/д") {
      return <span className="text-ink-muted">{formatted}</span>;
    }
    const n = parseNumeric(effectiveValue);
    const tone = DeltaTone({ trust, format, n });
    const Icon = n !== null && n > 0 ? TrendingUp : n !== null && n < 0 ? TrendingDown : BarChart3;
    return (
      <StatusBadge tone={tone}>
        <span className="inline-flex items-center gap-1">
          <Icon className="h-3 w-3" />
          {formatted}
        </span>
      </StatusBadge>
    );
  }

  const n = parseNumeric(effectiveValue);
  if (n === null) return <span className="text-ink-muted">—</span>;
  const positive = n > 0;
  const negative = n < 0;
  const tone = positive ? "ok" : negative ? "bad" : "info";
  const Icon = positive ? TrendingUp : negative ? TrendingDown : BarChart3;
  const formatted =
    format === "pct"
      ? formatDeltaWithTrust(n, "full", "pct")
      : format === "int"
        ? (n > 0 ? "+" : "") + formatInteger(n)
        : formatDeltaWithTrust(n, "full", "rub");

  return (
    <StatusBadge tone={tone}>
      <span className="inline-flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {formatted}
      </span>
    </StatusBadge>
  );
}
