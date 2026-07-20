import { formatProfitValue, type ProfitTrustContext } from "../../state/profit-trust";
import { formatRub } from "../../utils/format";
import { Card } from "../../ui/card";
import { TrustChip } from "../../ui/trust-chip";

export type PrimaryAnswerProps = {
  revenue: string | number | null | undefined;
  profit: string | number | null | undefined;
  trustCtx: ProfitTrustContext;
  isLoading?: boolean;
};

/** Dashboard primary answer block — revenue, profit, trust (F2-A2). No new calculations. */
export function PrimaryAnswer({ revenue, profit, trustCtx, isLoading }: PrimaryAnswerProps) {
  return (
    <Card
      className="border-brand/20 bg-gradient-to-br from-brand-subtle/80 to-surface p-6 shadow-soft"
      data-testid="primary-answer"
    >
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div>
          <div className="text-sm font-medium text-ink-muted">Выручка</div>
          <div className="mt-2 text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            {isLoading ? "…" : formatRub(revenue)}
          </div>
        </div>
        <div>
          <div className="text-sm font-medium text-ink-muted">Чистая прибыль</div>
          <div className="mt-2 text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            {isLoading ? "…" : formatProfitValue(profit, trustCtx.trust)}
          </div>
        </div>
      </div>
      <TrustChip trustContext={trustCtx} className="mt-4" />
    </Card>
  );
}
