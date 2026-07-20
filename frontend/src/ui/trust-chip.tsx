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
import { TRUST_BADGE_SPEC } from "./design-tokens";

type TrustChipTone = "ok" | "warn" | "bad";

export type TrustChipProps = {
  trustContext: ProfitTrustContext;
  className?: string;
  /** Defaults to TRUST_BADGE_SPEC.testId when used as Overview Trust badge. */
  "data-testid"?: string;
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
      return "border-ledger-profit/30 bg-ledger-profit-soft";
    case "warn":
      return "border-ledger-warn/30 bg-ledger-warn-soft";
    case "bad":
      return "border-ledger-risk/30 bg-ledger-risk-soft";
  }
}

/**
 * Compact trust + coverage indicator.
 * On Overview this is the sole Trust badge/line (static, under Primary Answer).
 */
export function TrustChip({ trustContext, className, "data-testid": testId }: TrustChipProps) {
  const { trust, coveragePct, coveredSkus, totalSkus } = trustContext;
  const tone = toneForTrust(trust);
  const label = profitTrustLabel(trust);
  const tooltip = profitTrustTooltip(trust, trustContext);

  const coverageText = coveragePct !== null ? formatPct(coveragePct) : null;
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
      data-testid={testId ?? TRUST_BADGE_SPEC.testId}
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
