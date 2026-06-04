import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Package, Snowflake, Skull, Timer } from "lucide-react";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { formatInteger, formatMetric, formatRub } from "../../utils/format";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { KpiCard } from "../../ui/kpi-card";
import { Select } from "../../ui/field";
import { PeriodSelector } from "../../ui/period-selector";
import { loadPeriodSelection, type PeriodSelection } from "../../state/period";
import { StatusBadge } from "../../ui/status-badge";

export function InventoryEconomicsPage() {
  const workspace = loadWorkspaceProfile();
  const defaultMarketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const [marketplace, setMarketplace] = useState<string>(defaultMarketplace);
  const [periodSel, setPeriodSel] = useState<PeriodSelection>(() => loadPeriodSelection());

  const start = periodSel.range.start;
  const end = periodSel.range.end;

  const inv = useQuery({
    queryKey: ["analytics", "inventoryEconomics", marketplace, start, end],
    queryFn: () => api.analytics.inventoryEconomics({ marketplace, start, end, limit: 50 }),
  });
  const slow = useQuery({
    queryKey: ["analytics", "inventorySlowMovers", marketplace, start, end],
    queryFn: () => api.analytics.inventorySlowMovers({ marketplace, start, end, threshold_days: 30, limit: 30 }),
  });
  const dead = useQuery({
    queryKey: ["analytics", "inventoryDeadStock", marketplace, start, end],
    queryFn: () => api.analytics.inventoryDeadStock({ marketplace, start, end, threshold_days: 60, limit: 30 }),
  });

  const integrity = inv.data?.integrity ?? null;
  const warnings = integrity?.warnings ?? [];

  const summary = useMemo(() => {
    const items = inv.data?.items ?? [];
    const frozen = items.reduce((acc, r) => acc + Number(r.frozen_capital ?? 0), 0);
    const stock = items.reduce((acc, r) => acc + (r.stock_units ?? 0), 0);
    return { frozen, stock };
  }, [inv.data]);

  return (
    <div className="page-shell">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="page-title">Склад и оборот</h1>
          <p className="page-subtitle">
            Оборот, замороженный капитал, медленные товары и «мертвые» остатки — без прогнозов, только детерминированная аналитика.
          </p>
        </div>
        <Select
          value={marketplace}
          onChange={(e) => setMarketplace(e.target.value)}
          className="h-9 w-auto min-w-[10rem]"
        >
          <option value="wildberries">Wildberries</option>
          <option value="ozon">Ozon</option>
        </Select>
      </div>

      <PeriodSelector onChange={setPeriodSel} />

      {warnings.length ? (
        <Card className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm font-semibold">Доверие к данным</div>
            <div className="flex flex-wrap gap-2">
              {integrity?.financial_completeness_score ? (
                <StatusBadge tone="info">
                  Полнота: {formatMetric(integrity.financial_completeness_score)} / 100
                </StatusBadge>
              ) : null}
              <StatusBadge tone="warn">Предупреждений: {warnings.length}</StatusBadge>
            </div>
          </div>
          <ul className="mt-3 space-y-1 text-xs text-ink-secondary">
            {warnings.slice(0, 4).map((w) => (
              <li key={w.code + w.message}>- {w.message}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      <div className="kpi-row">
        <KpiCard
          variant="hero"
          icon={<Snowflake className="h-5 w-5" />}
          label="Замороженный капитал (топ-50 SKU)"
          value={formatRub(summary.frozen)}
          sub="Расчёт: остаток × себестоимость (если задана)"
        />
        <KpiCard
          icon={<Package className="h-5 w-5" />}
          label="Остатки (ед.)"
          value={formatInteger(summary.stock)}
          sub={`Снимок: ${inv.data?.snapshot_date ?? "—"}`}
        />
        <KpiCard
          icon={<Timer className="h-5 w-5" />}
          label="Медленные / мёртвые"
          value={`${formatInteger(slow.data?.items.length ?? 0)} / ${formatInteger(dead.data?.items.length ?? 0)}`}
          sub="Пороги: 30 / 60 дней без продаж"
        />
      </div>

      <Card className="p-4">
        <div className="text-sm font-semibold">Оборот и риск по SKU (топ-50 по замороженному капиталу)</div>
        <div className="mt-3 overflow-auto">
          <table className="table-shell w-full min-w-[1000px] text-sm">
            <thead className="text-left">
              <tr>
                <th className="py-2">SKU</th>
                <th className="py-2">Остаток</th>
                <th className="py-2">Продано (период)</th>
                <th className="py-2">Средний остаток</th>
                <th className="py-2">Оборот (раз)</th>
                <th className="py-2">Оборот (дней)</th>
                <th className="py-2">Заморожено</th>
                <th className="py-2">Дней без продаж</th>
                <th className="py-2">Риск</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-subtle">
              {(inv.data?.items ?? []).map((r) => (
                <tr key={r.sku} className="hover:bg-surface-inset">
                  <td className="py-2 font-medium">{r.sku}</td>
                  <td className="py-2">{formatInteger(r.stock_units)}</td>
                  <td className="py-2">{formatInteger(r.sold_units)}</td>
                  <td className="py-2">{formatMetric(r.avg_stock_units ?? null)}</td>
                  <td className="py-2">{formatMetric(r.turnover_ratio ?? null)}</td>
                  <td className="py-2">{formatMetric(r.turnover_days ?? null)}</td>
                  <td className="py-2">{formatRub(r.frozen_capital ?? null)}</td>
                  <td className="py-2">{r.days_since_last_sale ?? "—"}</td>
                  <td className="py-2">
                    {r.stock_risk === "stockout" ? (
                      <StatusBadge tone="warn">Риск дефицита</StatusBadge>
                    ) : r.stock_risk === "overstock" ? (
                      <StatusBadge tone="bad">Риск залежей</StatusBadge>
                    ) : (
                      <StatusBadge tone="ok">Ок</StatusBadge>
                    )}
                  </td>
                </tr>
              ))}
              {!inv.isLoading && !(inv.data?.items?.length ?? 0) ? (
                <tr>
                  <td className="py-6 text-ink-muted" colSpan={9}>
                    Нет данных по складу за выбранный период.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>

      <CollapsibleSection title="Медленные и мёртвые остатки" subtitle="Пороги 30 и 60 дней без продаж">
      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="p-4">
          <div className="flex items-center gap-2 section-title">
            <Timer className="h-4 w-4" /> Медленные товары (≥30 дней без продаж)
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-ink-muted">
                <tr>
                  <th className="py-2">SKU</th>
                  <th className="py-2">Остаток</th>
                  <th className="py-2">Заморожено</th>
                  <th className="py-2">Дней без продаж</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-subtle">
                {(slow.data?.items ?? []).map((r) => (
                  <tr key={r.sku}>
                    <td className="py-2 font-medium">{r.sku}</td>
                    <td className="py-2">{formatInteger(r.stock_units)}</td>
                    <td className="py-2">{formatRub(r.frozen_capital ?? null)}</td>
                    <td className="py-2">{r.days_since_last_sale}</td>
                  </tr>
                ))}
                {!slow.isLoading && !(slow.data?.items?.length ?? 0) ? (
                  <tr>
                    <td className="py-6 text-ink-muted" colSpan={4}>
                      Нет медленных товаров по выбранным критериям.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Skull className="h-4 w-4" /> Мертвые остатки (≥60 дней без продаж)
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-ink-muted">
                <tr>
                  <th className="py-2">SKU</th>
                  <th className="py-2">Остаток</th>
                  <th className="py-2">Заморожено</th>
                  <th className="py-2">Дней без продаж</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-subtle">
                {(dead.data?.items ?? []).map((r) => (
                  <tr key={r.sku}>
                    <td className="py-2 font-medium">{r.sku}</td>
                    <td className="py-2">{formatInteger(r.stock_units)}</td>
                    <td className="py-2">{formatRub(r.frozen_capital ?? null)}</td>
                    <td className="py-2">{r.days_since_last_sale}</td>
                  </tr>
                ))}
                {!dead.isLoading && !(dead.data?.items?.length ?? 0) ? (
                  <tr>
                    <td className="py-6 text-ink-muted" colSpan={4}>
                      Мертвые остатки не обнаружены.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
      </CollapsibleSection>

      {inv.error ? <div className="text-sm text-semantic-danger">Ошибка загрузки складской аналитики.</div> : null}
    </div>
  );
}

