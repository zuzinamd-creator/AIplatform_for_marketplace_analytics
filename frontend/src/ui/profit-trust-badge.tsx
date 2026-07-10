import { StatusBadge } from "./status-badge";
import { cx } from "./cx";
import {
  marginTrustTooltip,
  profitTrustLabel,
  profitTrustTooltip,
  type ProfitTrustContext,
  type ProfitTrustLevel,
} from "../state/profit-trust";

type Props = {
  trust: ProfitTrustLevel;
  size?: "sm" | "md";
  showLabel?: boolean;
  tooltip?: boolean;
  trustContext?: Pick<ProfitTrustContext, "coveragePct" | "coveredSkus" | "totalSkus">;
  metric?: "profit" | "margin";
  className?: string;
};

function toneForTrust(trust: ProfitTrustLevel): "ok" | "warn" | "bad" {
  switch (trust) {
    case "full":
      return "ok";
    case "partial":
      return "warn";
    case "insufficient":
      return "bad";
  }
}

export function ProfitTrustBadge({
  trust,
  size = "sm",
  showLabel = true,
  tooltip = true,
  trustContext,
  metric = "profit",
  className,
}: Props) {
  const label = profitTrustLabel(trust);
  const tooltipText =
    metric === "margin"
      ? marginTrustTooltip(trust)
      : profitTrustTooltip(trust, trustContext ?? { coveragePct: null, coveredSkus: null, totalSkus: null });

  return (
    <span
      className={cx("inline-flex", className)}
      title={tooltip ? tooltipText : undefined}
      aria-label={tooltipText}
    >
      <span
        className={cx(
          "inline-flex",
          size === "sm" && "[&>span]:px-2 [&>span]:py-0.5 [&>span]:text-[10px]",
          size === "md" && "[&>span]:px-2.5 [&>span]:py-1 [&>span]:text-xs",
        )}
      >
        <StatusBadge tone={toneForTrust(trust)}>{showLabel ? label : "•"}</StatusBadge>
      </span>
    </span>
  );
}
