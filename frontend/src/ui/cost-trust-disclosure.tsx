import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../state/http";
import { loadWorkspaceProfile } from "../state/onboarding";
import { loadPeriodSelection } from "../state/period";
import {
  COSTS_WORKFLOW_ROUTE,
  COST_COVERAGE_ROUTE,
  marginTrustTooltip,
  profitTrustTooltip,
  useProfitTrust,
} from "../state/profit-trust";
import { Card } from "./card";
import { CostCoverageIndicator } from "./cost-coverage-indicator";
import { ProfitTrustBadge } from "./profit-trust-badge";

type Props = {
  marketplace?: string;
  start?: string;
  end?: string;
  className?: string;
};

/**
 * AI-facing cost trust disclosure — UI only, no prompt or AI logic changes.
 */
export function CostTrustDisclosure({ marketplace: mp, start: startProp, end: endProp, className }: Props) {
  const workspace = loadWorkspaceProfile();
  const marketplace = mp ?? (workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace);
  const period = loadPeriodSelection().range;
  const start = startProp ?? period.start;
  const end = endProp ?? period.end;

  const revenue = useQuery({
    queryKey: ["costTrustDisclosure", "revenue", marketplace, start, end],
    queryFn: () => api.analytics.revenueSummary({ marketplace, start, end }),
    staleTime: 60_000,
  });

  const coverage = useQuery({
    queryKey: ["costTrustDisclosure", "coverage", marketplace, start, end],
    queryFn: () => api.analytics.costCoverage({ marketplace, start, end, limit: 1 }),
    staleTime: 60_000,
  });

  const trustCtx = useProfitTrust(revenue.data?.integrity, coverage.data ?? null);

  const disclaimer =
    trustCtx.trust === "insufficient"
      ? "Рекомендации по прибыли и марже недоступны или с пониженной уверенностью — загрузите себестоимость."
      : trustCtx.trust === "partial"
        ? "Прибыль в рекомендациях может быть оценочной: себестоимость указана не для всех SKU. Маржа скрыта."
        : "Себестоимость покрывает все продаваемые SKU — финансовые рекомендации опираются на проверенную прибыль.";

  return (
    <Card className={className ?? "p-4"}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-ink-muted">Доверие к прибыли (COGS)</span>
        <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
      </div>
      {trustCtx.coveredSkus !== null && trustCtx.totalSkus !== null ? (
        <div className="mt-3">
          <CostCoverageIndicator
            coveredSkus={trustCtx.coveredSkus}
            totalSkus={trustCtx.totalSkus}
            coveragePct={trustCtx.coveragePct}
            variant="pill"
            showCta={trustCtx.trust !== "full"}
          />
        </div>
      ) : null}
      <p className="mt-3 text-xs leading-relaxed text-ink-secondary">{disclaimer}</p>
      <p className="mt-2 text-[11px] text-ink-muted" title={marginTrustTooltip(trustCtx.trust)}>
        {profitTrustTooltip(trustCtx.trust, trustCtx)}
      </p>
      {trustCtx.trust !== "full" ? (
        <div className="mt-3 flex flex-wrap gap-3 text-xs">
          <Link to={COSTS_WORKFLOW_ROUTE} className="link-muted">
            Загрузить себестоимость →
          </Link>
          <Link to={COST_COVERAGE_ROUTE} className="link-muted">
            Покрытие себестоимости →
          </Link>
        </div>
      ) : null}
    </Card>
  );
}
