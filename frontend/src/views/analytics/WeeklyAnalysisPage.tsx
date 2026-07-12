import React, { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  Layers3,
  PackageSearch,
  TrendingDown,
  TrendingUp,
  Warehouse,
} from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { previousPeriod } from "../../state/period";
import { usePagePeriod } from "../../state/use-page-period";
import {
  ANALYTICS_COST_COVERAGE_ROUTE,
  ANALYTICS_ECONOMICS_ROUTE,
  ANALYTICS_OVERVIEW_ROUTE,
} from "../../shell/analytics-tabs";
import { formatProfitValue, guardPeriodCompareDeltaProfit, showInlineCostTrustBanner, useProfitTrust } from "../../state/profit-trust";
import { formatInteger, formatPct, formatRub, parseNumeric } from "../../utils/format";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { CostCoverageIndicator } from "../../ui/cost-coverage-indicator";
import { CostTrustBanner } from "../../ui/cost-trust-banner";
import { KpiCard } from "../../ui/kpi-card";
import { Select } from "../../ui/field";
import { PeriodSelector } from "../../ui/period-selector";
import { ProfitTrustBadge } from "../../ui/profit-trust-badge";
import { StatusBadge } from "../../ui/status-badge";
import { TrustDeltaBadge } from "../../ui/trust-delta-badge";
import { WarnCallout } from "../../ui/warn-callout";

function SectionState(props: { loading: boolean; error: Error | null; empty: boolean; emptyText: string; children: React.ReactNode }) {
  if (props.loading) {
    return <div className="py-8 text-center text-sm text-ink-muted">Загрузка…</div>;
  }
  if (props.error) {
    return (
      <WarnCallout title="Не удалось загрузить данные">
        {props.error instanceof Error ? props.error.message : "Неизвестная ошибка"}
      </WarnCallout>
    );
  }
  if (props.empty) {
    return <div className="py-8 text-center text-sm text-ink-muted">{props.emptyText}</div>;
  }
  return <>{props.children}</>;
}

const INVENTORY_ECONOMICS_ROUTE = "/app/economics/inventory";

export function WeeklyAnalysisPage() {
  const workspace = loadWorkspaceProfile();
  const defaultMarketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const [marketplace, setMarketplace] = useState<"wildberries" | "ozon">(defaultMarketplace as "wildberries" | "ozon");
  const { periodSel, setPeriodSel } = usePagePeriod();

  useEffect(() => {
    if (!periodSel.compareEnabled) {
      setPeriodSel((prev) => ({
        ...prev,
        compareEnabled: true,
        comparePreset: "previous_period",
        compareRange: previousPeriod(prev.range),
      }));
    }
  }, [periodSel.compareEnabled, setPeriodSel]);

  const rangeA = periodSel.range;
  const rangeB = useMemo(() => {
    if (!periodSel.compareEnabled) return previousPeriod(rangeA);
    if (periodSel.comparePreset === "custom" && periodSel.compareRange) return periodSel.compareRange;
    return previousPeriod(rangeA);
  }, [periodSel, rangeA]);

  const snapshotDate = rangeA.end;

  const compare = useQuery({
    queryKey: ["analytics", "periodCompare", marketplace, rangeA, rangeB],
    queryFn: () =>
      api.analytics.periodCompare({
        marketplace,
        a_start: rangeA.start,
        a_end: rangeA.end,
        b_start: rangeB.start,
        b_end: rangeB.end,
      }),
  });

  const abc = useQuery({
    queryKey: ["analytics", "abc", marketplace, rangeA.start, rangeA.end],
    queryFn: () => api.analytics.abcAnalysis({ marketplace, start: rangeA.start, end: rangeA.end }),
  });

  const inventoryRisk = useQuery({
    queryKey: ["analytics", "inventoryRisk", snapshotDate],
    queryFn: () => api.analytics.inventoryRisk({ snapshot_date: snapshotDate }),
  });

  const inventorySkus = useQuery({
    queryKey: ["analytics", "inventoryEconomics", "weekly", marketplace, rangeA.start, rangeA.end],
    queryFn: () => api.analytics.inventoryEconomics({ marketplace, start: rangeA.start, end: rangeA.end, limit: 100 }),
  });

  const warehouses = useQuery({
    queryKey: ["analytics", "warehouses", snapshotDate],
    queryFn: () => api.analytics.warehouseAnalytics({ snapshot_date: snapshotDate }),
  });

  const costCoverage = useQuery({
    queryKey: ["analytics", "costCoverage", marketplace, rangeA.start, rangeA.end],
    queryFn: () => api.analytics.costCoverage({ marketplace, start: rangeA.start, end: rangeA.end, limit: 1 }),
  });

  const trustCtx = useProfitTrust(compare.data?.integrity, costCoverage.data ?? null);

  const deltaOrders = useMemo(() => {
    if (!compare.data) return null;
    return compare.data.a.units_sold - compare.data.b.units_sold;
  }, [compare.data]);

  const abcBuckets = useMemo(() => {
    const map = new Map((abc.data?.buckets ?? []).map((b) => [b.bucket, b]));
    return ["A", "B", "C"].map((bucket) => map.get(bucket) ?? { bucket, sku_count: 0, revenue: "0", revenue_pct: "0" });
  }, [abc.data]);

  const riskSkus = useMemo(() => {
    const items = inventorySkus.data?.items ?? [];
    const overstock = items.filter((i) => i.stock_risk === "overstock").slice(0, 15);
    const stockout = items.filter((i) => i.stock_risk === "stockout").slice(0, 15);
    return { overstock, stockout };
  }, [inventorySkus.data]);

  const warehouseRows = warehouses.data?.items ?? [];
  const stale =
    compare.data?.freshness?.stale_data_warning ||
    abc.data?.freshness?.stale_data_warning ||
    inventoryRisk.data?.stale_data_warning;

  const priorities = useMemo(() => {
    const list: Array<{ tone: "bad" | "warn" | "info"; text: string }> = [];
    if ((inventoryRisk.data?.high_discrepancy_warehouses ?? 0) > 0) {
      list.push({
        tone: "bad",
        text: `Проверьте ${inventoryRisk.data!.high_discrepancy_warehouses} склад(ов) с расхождениями остатков`,
      });
    }
    if (riskSkus.stockout.length > 0) {
      list.push({ tone: "bad", text: `Пополните остатки: ${riskSkus.stockout.length} SKU в зоне дефицита` });
    }
    if (riskSkus.overstock.length > 0) {
      list.push({ tone: "warn", text: `Снизьте закупку: ${riskSkus.overstock.length} SKU с риском затоваривания` });
    }
    if (trustCtx.trust === "partial") {
      list.push({
        tone: "warn",
        text: "Прибыль рассчитана не для всех SKU — не используйте её как единственный критерий решений",
      });
    } else if (trustCtx.trust === "full" && trustCtx.canShowProfitAction) {
      const guardedDelta = guardPeriodCompareDeltaProfit(
        compare.data?.delta_profit,
        trustCtx.trust,
        compare.data?.a.total_profit,
        compare.data?.b.total_profit,
      );
      const deltaProfit = parseNumeric(guardedDelta);
      if (deltaProfit !== null && deltaProfit < 0) {
        list.push({
          tone: "warn",
          text: "Прибыль снизилась относительно предыдущего периода — проверьте ABC-группу C",
        });
      }
    }
    if (list.length === 0) {
      list.push({ tone: "info", text: "Критичных складских рисков не обнаружено за выбранный период" });
    }
    return list;
  }, [compare.data, inventoryRisk.data, riskSkus, trustCtx]);

  return (
    <div className="page-shell">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="page-title">Сравнение периодов</h1>
          <p className="page-subtitle">
            Сравнение показателей между двумя периодами: выручка, прибыль, маржа, ABC и складские риски.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link className="btn-secondary" to={ANALYTICS_OVERVIEW_ROUTE}>
            Вернуться к обзору бизнеса
          </Link>
          <Link className="btn-secondary" to={ANALYTICS_ECONOMICS_ROUTE}>
            Экономика SKU →
          </Link>
          <Link className="btn-secondary" to={ANALYTICS_COST_COVERAGE_ROUTE}>
            Покрытие себестоимости →
          </Link>
          <Link className="btn-secondary" to={INVENTORY_ECONOMICS_ROUTE}>
            Склад и оборот →
          </Link>
          <StatusBadge tone={stale ? "warn" : "info"}>{stale ? "данные устарели" : "актуально"}</StatusBadge>
          <Select
            value={marketplace}
            onChange={(e) => setMarketplace(e.target.value as "wildberries" | "ozon")}
            className="h-9 w-auto min-w-[10rem]"
          >
            <option value="wildberries">Wildberries</option>
            <option value="ozon">Ozon</option>
          </Select>
        </div>
      </div>

      <PeriodSelector value={periodSel} onChange={setPeriodSel} />

      {showInlineCostTrustBanner() && trustCtx.trust !== "full" ? (
        <CostTrustBanner
          trust={trustCtx.trust}
          variant="inline"
          coveragePct={trustCtx.coveragePct}
          coveredSkus={trustCtx.coveredSkus}
          totalSkus={trustCtx.totalSkus}
          missingSkusSample={trustCtx.missingSkus.slice(0, 5)}
          storageKey={`weekly-${rangeA.start}-${rangeA.end}`}
        />
      ) : null}

      {trustCtx.coveredSkus !== null && trustCtx.totalSkus !== null ? (
        <CostCoverageIndicator
          coveredSkus={trustCtx.coveredSkus}
          totalSkus={trustCtx.totalSkus}
          coveragePct={trustCtx.coveragePct}
          variant="bar"
          showCta={trustCtx.trust !== "full"}
        />
      ) : null}

      <CollapsibleSection
        title="Сравнение периодов"
        subtitle={`Период A: ${rangeA.start} → ${rangeA.end} · Период B: ${rangeB.start} → ${rangeB.end}`}
        defaultOpen
      >
        <SectionState
          loading={compare.isLoading}
          error={compare.error as Error | null}
          empty={false}
          emptyText=""
        >
          {compare.data ? (
            <div className="space-y-4">
              <div className="kpi-row md:grid-cols-2 xl:grid-cols-4">
                <KpiCard
                  variant="hero"
                  icon={<BarChart3 className="h-5 w-5" />}
                  label="Изменение выручки"
                  value={<TrustDeltaBadge value={compare.data.delta_revenue} format="rub" />}
                  sub={`A: ${formatRub(compare.data.a.total_revenue)} · B: ${formatRub(compare.data.b.total_revenue)}`}
                />
                <KpiCard
                  icon={<TrendingUp className="h-5 w-5" />}
                  label={
                    <span className="inline-flex flex-wrap items-center gap-2">
                      Изменение прибыли
                      <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
                    </span>
                  }
                  value={
                    <TrustDeltaBadge
                      value={compare.data.delta_profit}
                      format="rub"
                      trust={trustCtx.trust}
                      aProfit={compare.data.a.total_profit}
                      bProfit={compare.data.b.total_profit}
                    />
                  }
                  sub={`A: ${formatProfitValue(compare.data.a.total_profit, trustCtx.trust)} · B: ${formatProfitValue(compare.data.b.total_profit, trustCtx.trust)}`}
                />
                <KpiCard
                  icon={<Layers3 className="h-5 w-5" />}
                  label={
                    <span className="inline-flex flex-wrap items-center gap-2">
                      Изменение маржинальности
                      <ProfitTrustBadge trust={trustCtx.trust} metric="margin" />
                    </span>
                  }
                  value={
                    <TrustDeltaBadge
                      value={compare.data.delta_margin_pct}
                      format="pct"
                      trust={trustCtx.trust}
                      aMargin={compare.data.a.margin_pct}
                      bMargin={compare.data.b.margin_pct}
                    />
                  }
                  sub={`A: ${trustCtx.canShowMargin ? formatPct(compare.data.a.margin_pct) : "—"} · B: ${trustCtx.canShowMargin ? formatPct(compare.data.b.margin_pct) : "—"}`}
                />
                <KpiCard
                  icon={<PackageSearch className="h-5 w-5" />}
                  label="Изменение заказов (ед.)"
                  value={<TrustDeltaBadge value={deltaOrders} format="int" />}
                  sub={`A: ${formatInteger(compare.data.a.units_sold)} · B: ${formatInteger(compare.data.b.units_sold)}`}
                />
              </div>
            </div>
          ) : null}
        </SectionState>
      </CollapsibleSection>

      <CollapsibleSection title="ABC-анализ" subtitle="Распределение выручки по группам A / B / C" defaultOpen>
        <SectionState
          loading={abc.isLoading}
          error={abc.error as Error | null}
          empty={!abc.data?.buckets?.length}
          emptyText="Нет SKU с выручкой за выбранный период. Загрузите отчёты продаж."
        >
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {abcBuckets.map((bucket) => (
              <Card key={bucket.bucket} className="p-5">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-lg font-semibold">Группа {bucket.bucket}</div>
                  <StatusBadge tone={bucket.bucket === "A" ? "ok" : bucket.bucket === "B" ? "info" : "warn"}>
                    {formatPct(bucket.revenue_pct)} выручки
                  </StatusBadge>
                </div>
                <div className="mt-3 text-2xl font-semibold text-ink">{formatRub(bucket.revenue)}</div>
                <div className="mt-1 text-xs text-ink-muted">SKU: {formatInteger(bucket.sku_count)}</div>
              </Card>
            ))}
          </div>
        </SectionState>
      </CollapsibleSection>

      <CollapsibleSection
        title="Риски запасов"
        subtitle="Дефицит, затоваривание и складские расхождения"
        defaultOpen
      >
        <SectionState
          loading={inventoryRisk.isLoading || inventorySkus.isLoading}
          error={(inventoryRisk.error ?? inventorySkus.error) as Error | null}
          empty={false}
          emptyText=""
        >
          <div className="space-y-4">
            <div className="kpi-row md:grid-cols-3">
              <KpiCard
                icon={<AlertTriangle className="h-5 w-5" />}
                label="Склады с расхождениями"
                value={formatInteger(inventoryRisk.data?.high_discrepancy_warehouses ?? 0)}
                sub={`Стоимость расхождений: ${formatRub(inventoryRisk.data?.discrepancy_cost_total)}`}
              />
              <KpiCard
                icon={<TrendingDown className="h-5 w-5" />}
                label="SKU в дефиците"
                value={formatInteger(riskSkus.stockout.length)}
                sub="stock_risk = stockout"
              />
              <KpiCard
                icon={<Boxes className="h-5 w-5" />}
                label="SKU с затовариванием"
                value={formatInteger(riskSkus.overstock.length)}
                sub="stock_risk = overstock"
              />
            </div>

            <Card className="p-4">
              <div className="text-sm font-semibold">Приоритеты действий</div>
              <ul className="mt-3 space-y-2">
                {priorities.map((p, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-ink-secondary">
                    <StatusBadge tone={p.tone}>{p.tone === "bad" ? "Высокий" : p.tone === "warn" ? "Средний" : "Инфо"}</StatusBadge>
                    <span>{p.text}</span>
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">Детализация по SKU</div>
                  <p className="mt-1 text-xs text-ink-muted">
                    Списки SKU в дефиците и затоваривании, оборот и медленные остатки — на странице «Склад и оборот».
                  </p>
                </div>
                <Link className="btn-secondary" to={INVENTORY_ECONOMICS_ROUTE}>
                  Склад и оборот →
                </Link>
              </div>
            </Card>
          </div>
        </SectionState>
      </CollapsibleSection>

      <CollapsibleSection
        title="Складская аналитика"
        subtitle={`Снимок на ${snapshotDate}`}
        defaultOpen
      >
        <SectionState
          loading={warehouses.isLoading}
          error={warehouses.error as Error | null}
          empty={warehouseRows.length === 0}
          emptyText="Нет складских снимков за выбранную дату. Загрузите отчёты с остатками."
        >
          <div className="kpi-row md:grid-cols-3">
            <KpiCard
              icon={<Warehouse className="h-5 w-5" />}
              label="Складов в снимке"
              value={formatInteger(warehouseRows.length)}
            />
            <KpiCard
              label="Фактические остатки (ед.)"
              value={formatInteger(warehouseRows.reduce((acc, r) => acc + r.actual_stock, 0))}
            />
            <KpiCard
              label="Расхождения (ед.)"
              value={formatInteger(warehouseRows.reduce((acc, r) => acc + Math.abs(r.discrepancy_units), 0))}
              sub={`Стоимость: ${formatRub(warehouseRows.reduce((acc, r) => acc + Number(r.discrepancy_cost ?? 0), 0))}`}
            />
          </div>

          <div className="mt-4 overflow-auto">
            <table className="table-shell w-full min-w-[960px] text-sm">
              <thead className="text-left text-xs text-ink-muted">
                <tr>
                  <th className="py-2">Склад</th>
                  <th className="py-2">Открытие</th>
                  <th className="py-2">Продано</th>
                  <th className="py-2">Факт</th>
                  <th className="py-2">Ожидание</th>
                  <th className="py-2">Расхождение</th>
                  <th className="py-2">Стоимость расх.</th>
                </tr>
              </thead>
              <tbody>
                {warehouseRows.map((row, idx) => (
                  <tr key={`${row.warehouse_name ?? "wh"}-${idx}`}>
                    <td className="py-2">{row.warehouse_name ?? "—"}</td>
                    <td className="py-2">{formatInteger(row.opening_stock)}</td>
                    <td className="py-2">{formatInteger(row.sold_units)}</td>
                    <td className="py-2">{formatInteger(row.actual_stock)}</td>
                    <td className="py-2">{formatInteger(row.expected_closing_stock)}</td>
                    <td className="py-2">
                      <StatusBadge tone={row.discrepancy_units !== 0 ? "warn" : "ok"}>
                        {formatInteger(row.discrepancy_units)}
                      </StatusBadge>
                    </td>
                    <td className="py-2">{formatRub(row.discrepancy_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionState>
      </CollapsibleSection>
    </div>
  );
}
