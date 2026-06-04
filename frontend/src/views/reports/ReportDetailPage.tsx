import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";

function toneForStatus(status?: string) {
  const s = (status ?? "").toLowerCase();
  if (s.includes("fail") || s.includes("dead")) return "bad" as const;
  if (s.includes("process")) return "info" as const;
  if (s.includes("complete") || s.includes("processed")) return "ok" as const;
  return "warn" as const;
}

function fmtPeriod(start?: string | null, end?: string | null): string {
  const fmt = (iso?: string | null) => {
    if (!iso) return "—";
    const d = iso.slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return "—";
    const [y, m, day] = d.split("-");
    return `${day}.${m}.${y}`;
  };
  if (!start && !end) return "— (появится после обработки ETL)";
  if (start && end && start.slice(0, 10) === end.slice(0, 10)) return fmt(start);
  return `${fmt(start)} — ${fmt(end)}`;
}

export function ReportDetailPage() {
  const { reportId } = useParams();
  const q = useQuery({
    queryKey: ["reports", "get", reportId],
    queryFn: () => api.reports.get(reportId!),
    enabled: Boolean(reportId),
  });

  const r = q.data;

  return (
    <div className="page-shell">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Детали отчёта</h1>
          <p className="page-subtitle">Статус обработки берётся из очереди ETL (`etl_jobs`).</p>
        </div>
        <Link className="link-muted" to="/app/reports">
          ← К списку отчётов
        </Link>
      </div>

      {q.isLoading ? (
        <Card className="p-5">Загрузка…</Card>
      ) : r ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card className="p-5">
            <div className="text-sm font-semibold text-ink">Файл</div>
            <div className="mt-2 text-sm text-ink-secondary">{r.original_filename}</div>
            <div className="mt-1 font-mono text-[11px] text-ink-muted">{r.file_checksum}</div>
            <div className="mt-3">
              <StatusBadge tone={toneForStatus(r.status)}>{r.status}</StatusBadge>
            </div>
            {r.error_message ? (
              <div className="mt-3 rounded-lg border border-semantic-danger/30 bg-semantic-danger-bg p-3 text-xs text-semantic-danger">
                {r.error_message}
              </div>
            ) : null}
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold text-ink">Обработка</div>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-ink-muted">Маркетплейс</div>
                <div className="mt-1 text-ink-secondary">{r.marketplace}</div>
              </div>
              <div>
                <div className="text-xs text-ink-muted">Тип отчёта</div>
                <div className="mt-1 text-ink-secondary">{r.report_type}</div>
              </div>
              <div>
                <div className="text-xs text-ink-muted">Период данных</div>
                <div className="mt-1 font-medium text-ink-secondary">{fmtPeriod(r.period_start, r.period_end)}</div>
              </div>
              <div>
                <div className="text-xs text-ink-muted">Создан</div>
                <div className="mt-1 text-ink-secondary">{new Date(r.created_at).toLocaleString("ru-RU")}</div>
              </div>
              <div>
                <div className="text-xs text-ink-muted">Обработан</div>
                <div className="mt-1 text-ink-secondary">
                  {r.processed_at ? new Date(r.processed_at).toLocaleString("ru-RU") : "—"}
                </div>
              </div>
            </div>

            <div className="mt-4 rounded-lg border border-surface-subtle bg-surface-inset p-3">
              <div className="text-xs font-medium text-ink-secondary">Задача ETL</div>
              <pre className="mt-2 max-h-48 overflow-auto text-[11px] text-ink-muted">
                {JSON.stringify(r.job ?? null, null, 2)}
              </pre>
            </div>
          </Card>
        </div>
      ) : (
        <Card className="p-5">Отчёт не найден или недоступен для вашего аккаунта.</Card>
      )}
    </div>
  );
}
