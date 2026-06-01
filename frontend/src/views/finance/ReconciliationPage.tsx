import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { loadPeriodSelection } from "../../state/period";
import { Card } from "../../ui/card";
import { PeriodSelector } from "../../ui/period-selector";
import { StatusBadge } from "../../ui/status-badge";

function Row(props: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-t border-slate-800 py-2 text-sm">
      <div className="text-slate-300">{props.label}</div>
      <div className="text-slate-100">{props.value}</div>
    </div>
  );
}

export function ReconciliationPage() {
  const workspace = loadWorkspaceProfile();
  const marketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const initial = loadPeriodSelection();
  const [range, setRange] = useState(() => initial.range);

  const rec = useQuery({
    queryKey: ["analytics", "reconciliationPeriod", marketplace, range.start, range.end],
    queryFn: () => api.analytics.reconciliationPeriod({ marketplace, start: range.start, end: range.end }),
  });

  const stale = rec.data?.freshness?.stale_data_warning ?? false;
  const w = rec.data?.warnings ?? [];
  const b = rec.data?.breakdown;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">Финансовая сверка</div>
          <div className="text-sm text-slate-300">
            Детальный разбор: почему <span className="font-medium">выплата</span> не равна{" "}
            <span className="font-medium">прибыли</span>.
          </div>
        </div>
        <StatusBadge tone={stale ? "warn" : "info"}>{stale ? "данные устарели" : "актуально"}</StatusBadge>
      </div>

      <PeriodSelector onChange={(s) => setRange(s.range)} />

      {w.length ? (
        <Card className="border-amber-500/30 bg-amber-500/10 p-4">
          <div className="text-sm font-semibold text-amber-100">Предупреждения</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-100">
            {w.map((x) => (
              <li key={x.code}>{x.message}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Card className="p-4">
          <div className="text-sm font-semibold">Компоненты периода</div>
          <div className="mt-2 text-xs text-slate-400">
            Период: {range.start} → {range.end} · Маркетплейс: {marketplace}
          </div>
          {b ? (
            <div className="mt-4">
              <Row label="Выручка" value={b.revenue} />
              <Row label="Возвраты" value={b.returns_amount} />
              <Row label="Комиссии" value={b.commissions} />
              <Row label="Логистика" value={b.logistics} />
              <Row label="Хранение" value={b.storage} />
              <Row label="Реклама" value={b.ads} />
              <Row label="Штрафы" value={b.penalties} />
              <Row label="Эквайринг" value={b.acquiring} />
              <Row label="Удержания" value={b.deductions} />
              <Row label="Компенсации" value={b.compensation} />
              <Row label="COGS (себестоимость)" value={b.cogs} />
              <div className="mt-3 border-t border-slate-800 pt-3">
                <Row label="Расчётная выплата" value={b.expected_payout} />
                <Row label="Фактическая выплата" value={b.actual_payout} />
                <Row label="Разница выплат" value={b.payout_difference} />
                <Row label="Прибыль (contribution margin)" value={b.profit} />
              </div>
            </div>
          ) : (
            <div className="mt-4 text-sm text-slate-400">{rec.isLoading ? "Загрузка…" : "Нет данных."}</div>
          )}
        </Card>

        <Card className="p-4">
          <div className="text-sm font-semibold">Почему выплата ≠ прибыль</div>
          <div className="mt-3 text-sm text-slate-200">
            {b?.payout_is_not_profit_explanation ?? "—"}
          </div>
          <div className="mt-4 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3 text-xs text-slate-300">
            Если себестоимость отсутствует, прибыль и маржа будут неполными. Проверьте страницу “Себестоимость и покрытие
            затрат”.
          </div>
        </Card>
      </div>
    </div>
  );
}

