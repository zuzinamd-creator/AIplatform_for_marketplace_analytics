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

function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return "—";
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y}`;
}

function fmtPeriod(start?: string | null, end?: string | null): string {
  if (!start && !end) return "—";
  if (start && end && start === end) return fmtDate(start);
  if (start && end) return `${fmtDate(start)} — ${fmtDate(end)}`;
  return fmtDate(start ?? end);
}

const LIST_LIMIT = 200;

export function ReportsPage() {
  const [statusFilter, setStatusFilter] = useState("all");
  const q = useQuery({
    queryKey: ["reports", "list", 0, LIST_LIMIT],
    queryFn: () => api.reports.list(0, LIST_LIMIT),
  });

  const filtered = useMemo(() => {
    const rows = q.data ?? [];
    if (statusFilter === "all") return rows;
    return rows.filter((r) => String(r.status).toLowerCase().includes(statusFilter));
  }, [q.data, statusFilter]);

  const savedViews = loadSavedViews("reports");

  return (
    <div className="page-shell">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="page-title">Отчёты</h1>
          <p className="page-subtitle">Загрузки и их жизненный цикл обработки. Показаны только ваши отчёты.</p>
        </div>
        <Link className="btn-primary" to="/app/reports/upload">
          Загрузить отчёт
        </Link>
      </div>

      <Card className="p-5">
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
            <div className="text-xs text-ink-muted">Сохранено: {savedViews.map((v) => v.name).join(", ")}</div>
          ) : null}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="grid grid-cols-12 gap-0 border-b border-surface-subtle bg-surface-inset px-4 py-3 text-xs font-medium uppercase tracking-wide text-ink-muted">
          <div className="col-span-3">Файл</div>
          <div className="col-span-2">Маркетплейс</div>
          <div className="col-span-2">Период</div>
          <div className="col-span-2">Статус</div>
          <div className="col-span-3">Примечания</div>
        </div>

        {q.isLoading ? (
          <div className="px-4 py-6 text-sm text-ink-secondary">Загрузка…</div>
        ) : filtered.length > 0 ? (
          filtered.map((r) => (
            <Link
              key={r.id}
              to={`/app/reports/${r.id}`}
              className="grid grid-cols-12 gap-0 border-b border-surface-subtle px-4 py-3 text-sm transition hover:bg-surface-inset"
            >
              <div className="col-span-3 truncate font-medium text-ink-secondary">{r.original_filename}</div>
              <div className="col-span-2 truncate text-ink-muted">{r.marketplace}</div>
              <div className="col-span-2 truncate text-ink-secondary">{fmtPeriod(r.period_start, r.period_end)}</div>
              <div className="col-span-2">
                <StatusBadge tone={toneForStatus(r.status)}>{r.status}</StatusBadge>
              </div>
              <div className="col-span-3 truncate text-ink-muted">
                {r.error_message ? `Ошибка: ${r.error_message}` : r.job?.status ? `Задача: ${r.job.status}` : ""}
              </div>
            </Link>
          ))
        ) : q.data && q.data.length > 0 ? (
          <div className="px-4 py-10 text-center">
            <div className="text-sm font-medium">Нет отчётов по выбранному фильтру</div>
            <div className="mt-1 text-xs text-ink-muted">Смените фильтр статуса на «Все» или загрузите новый отчёт.</div>
          </div>
        ) : (
          <div className="px-4 py-10 text-center">
            <div className="text-sm font-medium">Отчётов пока нет</div>
            <div className="mt-1 text-xs text-ink-muted">
              Загрузите первый отчёт, чтобы построить проводки, снимки склада и получить рекомендации AI.
            </div>
            <div className="mt-3 text-xs text-ink-muted">
              Если отчёты были загружены ранее — проверьте, что вы вошли под тем же аккаунтом (email в боковой панели).
              Данные изолированы по пользователю и не удаляются при обновлении интерфейса.
            </div>
          </div>
        )}
        {(q.data?.length ?? 0) >= LIST_LIMIT ? (
          <div className="border-t border-surface-subtle px-4 py-2 text-xs text-ink-muted">
            Показаны последние {LIST_LIMIT} отчётов. Старые записи скрыты — при необходимости добавим постраничную навигацию.
          </div>
        ) : null}
      </Card>
    </div>
  );
}
