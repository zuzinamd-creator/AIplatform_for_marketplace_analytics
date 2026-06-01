import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Package, Snowflake, Skull, Timer } from "lucide-react";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { Card } from "../../ui/card";
import { PeriodSelector } from "../../ui/period-selector";
import { loadPeriodSelection, type PeriodSelection } from "../../state/period";
import { StatusBadge } from "../../ui/status-badge";

function rub(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 0 }) + " ₽";
}

function num(v: string | null | undefined): string {
  if (!v) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 1 });
}

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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xl font-semibold">Склад и оборот</div>
          <div className="mt-1 text-xs text-slate-400">
            Оборот, замороженный капитал, медленные товары и “мертвые” остатки — без прогнозов, только детерминированная аналитика.
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={marketplace}
            onChange={(e) => setMarketplace(e.target.value)}
            className="h-9 rounded-md border border-slate-800 bg-slate-950/40 px-2 text-sm"
          >
            <option value="wildberries">Wildberries</option>
            <option value="ozon">Ozon</option>
          </select>
          <PeriodSelector onChange={setPeriodSel} />
        </div>
      </div>

      {warnings.length ? (
        <Card className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm font-semibold">Доверие к данным</div>
            <div className="flex flex-wrap gap-2">
              {integrity?.financial_completeness_score ? (
                <StatusBadge tone="info">
                  Полнота: {Number(integrity.financial_completeness_score).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} / 100
                </StatusBadge>
              ) : null}
              <StatusBadge tone="warn">Предупреждений: {warnings.length}</StatusBadge>
            </div>
          </div>
          <ul className="mt-3 space-y-1 text-xs text-slate-300">
            {warnings.slice(0, 4).map((w) => (
              <li key={w.code + w.message}>- {w.message}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      <div className="grid gap-3 md:grid-cols-3">
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs text-slate-300">Замороженный капитал (топ-50 SKU)</div>
              <div className="mt-1 text-lg font-semibold">{rub(summary.frozen)}</div>
              <div className="mt-1 text-xs text-slate-400">Расчет: остаток × себестоимость (если задана).</div>
            </div>
            <div className="rounded-lg bg-slate-950/40 p-2 text-slate-200">
              <Snowflake className="h-5 w-5" />
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs text-slate-300">Остатки (ед.)</div>
              <div className="mt-1 text-lg font-semibold">{summary.stock.toLocaleString("ru-RU")}</div>
              <div className="mt-1 text-xs text-slate-400">Снимок: {inv.data?.snapshot_date ?? "—"}</div>
            </div>
            <div className="rounded-lg bg-slate-950/40 p-2 text-slate-200">
              <Package className="h-5 w-5" />
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-xs text-slate-300">Медленные / мертвые</div>
              <div className="mt-1 text-lg font-semibold">
                {slow.data?.items.length ?? 0} / {dead.data?.items.length ?? 0}
              </div>
              <div className="mt-1 text-xs text-slate-400">Пороги: 30 / 60 дней без продаж.</div>
            </div>
            <div className="rounded-lg bg-slate-950/40 p-2 text-slate-200">
              <Timer className="h-5 w-5" />
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="text-sm font-semibold">Оборот и риск по SKU (топ-50 по замороженному капиталу)</div>
        <div className="mt-3 overflow-auto">
          <table className="w-full min-w-[1000px] text-sm">
            <thead className="text-left text-xs text-slate-400">
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
            <tbody className="divide-y divide-slate-900/60">
              {(inv.data?.items ?? []).map((r) => (
                <tr key={r.sku} className="hover:bg-slate-950/30">
                  <td className="py-2 font-medium">{r.sku}</td>
                  <td className="py-2">{r.stock_units.toLocaleString("ru-RU")}</td>
                  <td className="py-2">{r.sold_units.toLocaleString("ru-RU")}</td>
                  <td className="py-2">{num(r.avg_stock_units ?? null)}</td>
                  <td className="py-2">{num(r.turnover_ratio ?? null)}</td>
                  <td className="py-2">{num(r.turnover_days ?? null)}</td>
                  <td className="py-2">{rub(r.frozen_capital ?? null)}</td>
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
                  <td className="py-6 text-slate-400" colSpan={9}>
                    Нет данных по складу за выбранный период.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Timer className="h-4 w-4" /> Медленные товары (≥30 дней без продаж)
          </div>
          <div className="mt-3 overflow-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-slate-400">
                <tr>
                  <th className="py-2">SKU</th>
                  <th className="py-2">Остаток</th>
                  <th className="py-2">Заморожено</th>
                  <th className="py-2">Дней без продаж</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900/60">
                {(slow.data?.items ?? []).map((r) => (
                  <tr key={r.sku}>
                    <td className="py-2 font-medium">{r.sku}</td>
                    <td className="py-2">{r.stock_units.toLocaleString("ru-RU")}</td>
                    <td className="py-2">{rub(r.frozen_capital ?? null)}</td>
                    <td className="py-2">{r.days_since_last_sale}</td>
                  </tr>
                ))}
                {!slow.isLoading && !(slow.data?.items?.length ?? 0) ? (
                  <tr>
                    <td className="py-6 text-slate-400" colSpan={4}>
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
              <thead className="text-left text-xs text-slate-400">
                <tr>
                  <th className="py-2">SKU</th>
                  <th className="py-2">Остаток</th>
                  <th className="py-2">Заморожено</th>
                  <th className="py-2">Дней без продаж</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900/60">
                {(dead.data?.items ?? []).map((r) => (
                  <tr key={r.sku}>
                    <td className="py-2 font-medium">{r.sku}</td>
                    <td className="py-2">{r.stock_units.toLocaleString("ru-RU")}</td>
                    <td className="py-2">{rub(r.frozen_capital ?? null)}</td>
                    <td className="py-2">{r.days_since_last_sale}</td>
                  </tr>
                ))}
                {!dead.isLoading && !(dead.data?.items?.length ?? 0) ? (
                  <tr>
                    <td className="py-6 text-slate-400" colSpan={4}>
                      Мертвые остатки не обнаружены.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {inv.error ? <div className="text-sm text-red-300">Ошибка загрузки складской аналитики.</div> : null}
    </div>
  );
}

