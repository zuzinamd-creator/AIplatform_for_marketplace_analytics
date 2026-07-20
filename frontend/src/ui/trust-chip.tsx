import { Link } from "react-router-dom";

import {
  COSTS_WORKFLOW_ROUTE,
  profitTrustLabel,
  profitTrustTooltip,
  type ProfitTrustContext,
} from "../state/profit-trust";
import { formatMetric, formatPct } from "../utils/format";
import { cx } from "./cx";
import { StatusBadge } from "./status-badge";

type TrustChipTone = "ok" | "warn" | "bad";

export type TrustChipProps = {
  trustContext: ProfitTrustContext;
  className?: string;
};

function toneForTrust(trust: ProfitTrustContext["trust"]): TrustChipTone {
  switch (trust) {
    case "full":
      return "ok";
    case "partial":
      return "warn";
    case "insufficient":
      return "bad";
  }
}

function chipSurfaceClass(tone: TrustChipTone): string {
  switch (tone) {
    case "ok":
      return "border-emerald-200/80 bg-semantic-success-bg/60";
    case "warn":
      return "border-amber-200/80 bg-semantic-warn-bg/60";
    case "bad":
      return "border-red-200/80 bg-semantic-danger-bg/60";
  }
}

/** Compact trust + coverage indicator for dashboard hero (F2-A1). No new trust logic. */
export function TrustChip({ trustContext, className }: TrustChipProps) {
  const { trust, coveragePct, coveredSkus, totalSkus } = trustContext;
  const tone = toneForTrust(trust);
  const label = profitTrustLabel(trust);
  const tooltip = profitTrustTooltip(trust, trustContext);

  const coverageText =
    coveragePct !== null ? formatPct(coveragePct) : null;
  const skuText =
    coveredSkus !== null && totalSkus !== null
      ? `${formatMetric(coveredSkus)} / ${formatMetric(totalSkus)} SKU`
      : null;

  return (
    <div
      className={cx(
        "inline-flex max-w-full flex-wrap items-center gap-2 rounded-lg border px-3 py-2 text-xs",
        chipSurfaceClass(tone),
        className,
      )}
      data-testid="trust-chip"
      role="status"
      aria-live="polite"
      title={tooltip}
    >
      <StatusBadge tone={tone}>{label}</StatusBadge>
      {coverageText ? (
        <span className="text-ink-secondary" data-testid="trust-chip-coverage">
          {coverageText}
        </span>
      ) : null}
      {skuText ? (
        <span className="text-ink-muted" data-testid="trust-chip-sku">
          {skuText}
        </span>
      ) : null}
      {trust !== "full" ? (
        <Link
          to={COSTS_WORKFLOW_ROUTE}
          className="link-muted shrink-0 font-medium"
          data-testid="trust-chip-cta"
        >
          Уточнить
        </Link>
      ) : null}
    </div>
  );
}
