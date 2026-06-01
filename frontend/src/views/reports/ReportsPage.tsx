import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";

import { api } from "../../state/http";
import { loadSavedViews, saveView } from "../../state/savedViews";
import { trackUsage } from "../../state/usage";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { Label, Select } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";

function toneForStatus(status?: string) {
  const s = (status ?? "").toLowerCase();
  if (s.includes("fail") || s.includes("dead")) return "bad" as const;
  if (s.includes("process")) return "info" as const;
  if (s.includes("complete") || s.includes("processed")) return "ok" as const;
  return "warn" as const;
}

export function ReportsPage() {
  const [statusFilter, setStatusFilter] = useState("all");
  const q = useQuery({
    queryKey: ["reports", "list", 0, 50],
    queryFn: () => api.reports.list(0, 50),
  });

  const filtered = useMemo(() => {
    const rows = q.data ?? [];
    if (statusFilter === "all") return rows;
    return rows.filter((r) => String(r.status).toLowerCase().includes(statusFilter));
  }, [q.data, statusFilter]);

  const savedViews = loadSavedViews("reports");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-2xl font-semibold">Отчёты</div>
          <div className="text-sm text-slate-300">Загрузки и их жизненный цикл обработки.</div>
        </div>
        <Link
          className="rounded-lg bg-sky-500/90 px-4 py-2 text-sm font-medium text-white hover:bg-sky-400"
          to="/app/reports/upload"
        >
          Загрузить отчёт
        </Link>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label>Фильтр по статусу</Label>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">Все</option>
              <option value="pending">Ожидает</option>
              <option value="process">Обработка</option>
              <option value="processed">Готово</option>
              <option value="fail">Ошибка</option>
            </Select>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              saveView({ name: `Отчёты: ${statusFilter}`, page: "reports", filter: { status: statusFilter } });
              trackUsage("save_view", { page: "reports" });
            }}
          >
            Сохранить вид
          </Button>
          {savedViews.length > 0 ? (
            <div className="text-xs text-slate-400">Сохранено: {savedViews.map((v) => v.name).join(", ")}</div>
          ) : null}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="grid grid-cols-12 gap-0 border-b border-slate-800/70 bg-slate-950/40 px-4 py-3 text-xs text-slate-300">
          <div className="col-span-3">Файл</div>
          <div className="col-span-2">Маркетплейс</div>
          <div className="col-span-2">Тип</div>
          <div className="col-span-2">Статус</div>
          <div className="col-span-3">Примечания</div>
        </div>

        {q.isLoading ? (
          <div className="px-4 py-6 text-sm text-slate-300">Загрузка…</div>
        ) : q.data && q.data.length > 0 ? (
          filtered.map((r) => (
            <Link
              key={r.id}
              to={`/app/reports/${r.id}`}
              className="grid grid-cols-12 gap-0 border-b border-slate-800/40 px-4 py-3 text-sm hover:bg-slate-900/40"
            >
              <div className="col-span-3 truncate">{r.original_filename}</div>
              <div className="col-span-2 truncate text-slate-200">{r.marketplace}</div>
              <div className="col-span-2 truncate text-slate-200">{r.report_type}</div>
              <div className="col-span-2">
                <StatusBadge tone={toneForStatus(r.status)}>{r.status}</StatusBadge>
              </div>
              <div className="col-span-3 truncate text-slate-300">
                {r.error_message ? `Ошибка: ${r.error_message}` : r.job?.status ? `Задача: ${r.job.status}` : ""}
              </div>
            </Link>
          ))
        ) : (
          <div className="px-4 py-10 text-center">
            <div className="text-sm font-medium">Отчётов пока нет</div>
            <div className="mt-1 text-xs text-slate-400">
              Загрузите первый отчёт, чтобы построить проводки, снимки склада и получить рекомендации AI.
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

