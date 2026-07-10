import { useMemo } from "react";

import type { AnalyticsIntegrityMeta, CostCoverageResponse } from "./types-analytics";
import { formatMetric, formatPct, formatRub, parseNumeric } from "../utils/format";

export type ProfitTrustLevel = "full" | "partial" | "insufficient";

export type ProfitTrustContext = {
  trust: ProfitTrustLevel;
  coveragePct: number | null;
  coveredSkus: number | null;
  totalSkus: number | null;
  missingSkus: string[];
  canShowProfit: boolean;
  canShowMargin: boolean;
  canShowProfitAction: boolean;
};

export const COSTS_WORKFLOW_ROUTE = "/app/costs";
export const COST_COVERAGE_ROUTE = "/app/finance/cost-coverage";

const TRUST_LEVELS: ProfitTrustLevel[] = ["full", "partial", "insufficient"];

/** Normalize API-provided trust — never derive from coverage on the frontend. */
export function normalizeProfitTrust(value: unknown): ProfitTrustLevel {
  if (typeof value === "string" && TRUST_LEVELS.includes(value as ProfitTrustLevel)) {
    return value as ProfitTrustLevel;
  }
  return "insufficient";
}

export function deriveProfitTrustContext(
  integrity?: AnalyticsIntegrityMeta | null,
  costCoverage?: CostCoverageResponse | null,
): ProfitTrustContext {
  const trust = normalizeProfitTrust(integrity?.profit_metrics_trust);

  const coveragePct = parseNumeric(
    costCoverage?.sku_cost_coverage_pct ?? integrity?.sku_cost_coverage_pct ?? null,
  );
  const coveredSkus = costCoverage?.covered_skus ?? null;
  const totalSkus = costCoverage?.total_skus ?? null;
  const missingSkus = costCoverage?.missing_skus ?? [];

  return {
    trust,
    coveragePct,
    coveredSkus,
    totalSkus,
    missingSkus,
    canShowProfit: trust !== "insufficient",
    canShowMargin: trust === "full",
    canShowProfitAction: trust === "full",
  };
}

export function useProfitTrust(
  integrity?: AnalyticsIntegrityMeta | null,
  costCoverage?: CostCoverageResponse | null,
): ProfitTrustContext {
  return useMemo(
    () => deriveProfitTrustContext(integrity, costCoverage),
    [integrity, costCoverage],
  );
}

/** Display profit KPI values according to backend trust contract. */
export function formatProfitValue(value: unknown, trust: ProfitTrustLevel): string {
  if (trust === "insufficient") {
    return "—";
  }
  const formatted = formatRub(value);
  if (formatted === "—") {
    return "—";
  }
  if (trust === "partial") {
    return `~${formatted}`;
  }
  return formatted;
}

/** Display profit/margin deltas according to backend trust contract. */
export function formatDeltaWithTrust(
  delta: unknown,
  trust: ProfitTrustLevel,
  format: "rub" | "pct",
): string {
  if (trust === "insufficient") {
    return "н/д";
  }

  const n = parseNumeric(delta);
  if (n === null) {
    return "—";
  }

  const core = format === "rub" ? formatRub(delta) : formatPct(delta);
  if (core === "—") {
    return "—";
  }

  const signed = n > 0 ? `+${core}` : core;
  if (trust === "partial") {
    return `~${signed}`;
  }
  return signed;
}

export function profitTrustLabel(trust: ProfitTrustLevel): string {
  switch (trust) {
    case "full":
      return "Проверено";
    case "partial":
      return "Оценка";
    case "insufficient":
      return "Нет себестоимости";
  }
}

export function profitTrustTooltip(
  trust: ProfitTrustLevel,
  ctx: Pick<ProfitTrustContext, "coveragePct" | "coveredSkus" | "totalSkus">,
): string {
  switch (trust) {
    case "full":
      return "Себестоимость указана для всех продаваемых SKU в периоде.";
    case "partial": {
      const pct = ctx.coveragePct !== null ? formatMetric(ctx.coveragePct, { suffix: " %" }) : null;
      const sku =
        ctx.coveredSkus !== null && ctx.totalSkus !== null
          ? `${ctx.coveredSkus} из ${ctx.totalSkus} SKU`
          : null;
      const parts = [
        "Прибыль рассчитана не для всех SKU.",
        pct ? `Покрытие: ${pct}.` : null,
        sku ? `Товаров: ${sku}.` : null,
        "Маржа скрыта как ненадёжная.",
      ].filter(Boolean);
      return parts.join(" ");
    }
    case "insufficient":
      return "Загрузите себестоимость, чтобы увидеть прибыль и маржу.";
  }
}

export function marginTrustTooltip(trust: ProfitTrustLevel): string {
  if (trust === "full") {
    return "Маржа доступна при полном покрытии себестоимости.";
  }
  if (trust === "partial") {
    return "Маржа скрыта: себестоимость указана не для всех SKU.";
  }
  return "Маржа недоступна без себестоимости.";
}
