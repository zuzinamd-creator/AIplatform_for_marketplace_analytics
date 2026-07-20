import { formatProfitValue, type ProfitTrustContext } from "../../state/profit-trust";
import { formatRub } from "../../utils/format";
import { Card } from "../../ui/card";
import { TrustChip } from "../../ui/trust-chip";
import { TRUST_BADGE_SPEC } from "../../ui/design-tokens";

export type PrimaryAnswerProps = {
  revenue: string | number | null | undefined;
  profit: string | number | null | undefined;
  trustCtx: ProfitTrustContext;
  isLoading?: boolean;
};

/**
 * Dashboard primary answer — revenue, profit, single Trust badge (Ledger UI P0).
 * No gradient; flat raised panel. Trust appears exactly once under metrics.
 */
export function PrimaryAnswer({ revenue, profit, trustCtx, isLoading }: PrimaryAnswerProps) {
  return (
    <Card
      className="border-surface-subtle bg-surface p-6 shadow-raised"
      data-testid="primary-answer"
    >
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div>
          <div className="text-sm font-medium text-ink-muted">Выручка</div>
          <div className="mt-2 text-3xl font-semibold tracking-tight text-ink tabular-nums md:text-4xl">
            {isLoading ? "…" : formatRub(revenue)}
          </div>
        </div>
        <div>
          <div className="text-sm font-medium text-ink-muted">Чистая прибыль</div>
          <div
            className={`mt-2 text-3xl font-semibold tracking-tight tabular-nums md:text-4xl ${
              trustCtx.canShowProfit && trustCtx.trust === "full" ? "text-ledger-profit" : "text-ink"
            }`}
          >
            {isLoading ? "…" : formatProfitValue(profit, trustCtx.trust)}
          </div>
        </div>
      </div>
      {/* Trust badge/line — sole Overview instance (see TRUST_BADGE_SPEC). Static, no animation. */}
      <TrustChip
        trustContext={trustCtx}
        className="mt-4"
        data-testid={TRUST_BADGE_SPEC.testId}
      />
    </Card>
  );
}
