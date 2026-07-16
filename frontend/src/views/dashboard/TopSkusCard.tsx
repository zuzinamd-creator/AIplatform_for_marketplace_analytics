import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import {
  formatMarginValue,
  formatProfitValue,
  type ProfitTrustContext,
} from "../../state/profit-trust";
import type { TopSkusResponse } from "../../state/types-analytics";
import { formatRub } from "../../utils/format";
import { Card } from "../../ui/card";
import {
  skuNeedsAttention,
  topSkuApiSortParam,
  type TopSkuSortTab,
} from "./top-sku-attention";

const ECONOMICS_ROUTE = "/app/economics";

const SORT_TABS: Array<{ id: TopSkuSortTab; label: string }> = [
  { id: "revenue", label: "Выручка" },
  { id: "profit", label: "Прибыль" },
  { id: "margin", label: "Маржа" },
];

export type TopSkusCardProps = {
  marketplace: string;
  start: string;
  end: string;
  /** Embedded summary payload (revenue sort); used when tab = Выручка. */
  summaryTopSkus: TopSkusResponse | null | undefined;
  trustCtx: ProfitTrustContext;
  coverageMin?: string | null;
  coverageMax?: string | null;
  missingPeriodsCount?: number;
  recommendationsCount?: number;
};

export function TopSkusCard({
  marketplace,
  start,
  end,
  summaryTopSkus,
  trustCtx,
  coverageMin,
  coverageMax,
  missingPeriodsCount = 0,
  recommendationsCount = 0,
}: TopSkusCardProps) {
  const [sortTab, setSortTab] = useState<TopSkuSortTab>("revenue");

  const sortedQuery = useQuery({
    queryKey: ["analytics", "topSkus", marketplace, start, end, sortTab],
    queryFn: () =>
      api.analytics.topSkus({
        marketplace,
        start,
        end,
        limit: 5,
        sort: topSkuApiSortParam(sortTab),
      }),
    enabled: sortTab !== "revenue",
  });

  const topSkus: TopSkusResponse | null | undefined =
    sortTab === "revenue" ? summaryTopSkus : sortedQuery.data;
  const items = topSkus?.items ?? [];
  const listLoading = sortTab !== "revenue" && sortedQuery.isLoading;
  const listError = sortTab !== "revenue" ? sortedQuery.error : null;

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-ink">Топ SKU</div>
          <div className="mt-2 text-xs text-ink-muted">
            Период: {start} → {end} · {marketplace}
          </div>
        </div>
        <Link to={ECONOMICS_ROUTE} className="link-muted shrink-0 text-xs">
          В Экономику товаров →
        </Link>
      </div>

      <div className="mt-4 flex flex-wrap gap-1" role="tablist" aria-label="Сортировка топа SKU">
        {SORT_TABS.map((tab) => {
          const active = sortTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              className={
                active
                  ? "rounded-lg bg-brand-subtle px-3 py-1.5 text-xs font-medium text-brand"
                  : "rounded-lg px-3 py-1.5 text-xs font-medium text-ink-muted hover:bg-surface-inset hover:text-ink-secondary"
              }
              onClick={() => setSortTab(tab.id)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="mt-5 space-y-3">
        {listLoading ? (
          <div className="text-sm text-ink-muted">Загрузка топа SKU…</div>
        ) : listError ? (
          <div className="text-sm text-danger">Не удалось загрузить топ SKU.</div>
        ) : items.length === 0 ? (
          <div className="text-sm text-ink-muted">Пока нет метрик по SKU.</div>
        ) : (
          items.map((row) => {
            const attention = skuNeedsAttention(row, items);
            return (
              <div
                key={row.sku}
                className={`flex items-start justify-between gap-3 border-b border-surface-subtle/60 pb-2 last:border-0 last:pb-0 ${
                  attention ? "rounded-md bg-amber-50/80 px-2 py-1.5 ring-1 ring-amber-200/80" : ""
                }`}
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-ink-secondary">{row.sku}</div>
                  {attention ? (
                    <div className="mt-0.5 text-[11px] text-amber-800">Требует внимания</div>
                  ) : null}
                </div>
                <div className="shrink-0 text-right text-xs text-ink-muted">
                  <div>
                    {formatRub(row.revenue)}
                    {" · "}
                    {row.units_sold} шт.
                  </div>
                  <div className="mt-0.5 text-[11px] text-ink-faint">
                    Прибыль: {formatProfitValue(row.net_profit, trustCtx.trust)}
                    {" · "}
                    Маржа: {formatMarginValue(row.margin_pct, trustCtx.trust)}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="mt-5 space-y-2 text-xs text-ink-muted">
        <div>
          Диапазон данных: {coverageMin ?? "—"} → {coverageMax ?? "—"}
        </div>
        {missingPeriodsCount ? <div>Есть пропуски в периодах: {missingPeriodsCount}</div> : null}
        {recommendationsCount ? <div>Рекомендации: {recommendationsCount}</div> : null}
      </div>
    </Card>
  );
}
