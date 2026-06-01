import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../state/http";
import { loadSettings } from "../state/settings";
import { Card } from "./card";
import { StatusBadge } from "./status-badge";

type Banner = {
  id: string;
  tone: "ok" | "warn" | "bad" | "info";
  title: string;
  detail: string;
  href?: string;
  action?: string;
};

function collectBanners(
  runtime: Record<string, unknown> | undefined,
  aiOps: Record<string, unknown> | undefined,
  reports: Array<{ status?: string }> | undefined,
): Banner[] {
  const settings = loadSettings();
  const banners: Banner[] = [];

  const rebuild = (runtime?.rebuild ?? {}) as Record<string, number>;
  const queue = (runtime?.queue ?? {}) as Record<string, number>;
  const health = (runtime?.health ?? {}) as Record<string, unknown>;
  const tenantState = String(runtime?.tenant_state ?? "");
  const workloadState = String(runtime?.workload_state ?? "");

  if (settings.rebuild_alerts && (rebuild.running ?? 0) > 0) {
    banners.push({
      id: "rebuild-running",
      tone: "info",
      title: "Обновление данных выполняется",
      detail: `В работе: ${rebuild.running}. Часть KPI может быть временно неактуальна до завершения.`,
      href: "/app/status",
      action: "Статус системы",
    });
  }

  if (settings.rebuild_alerts && (rebuild.pending_dispatch ?? 0) > 0) {
    banners.push({
      id: "rebuild-pending",
      tone: "warn",
      title: "Обновление данных в очереди",
      detail: `В очереди: ${rebuild.pending_dispatch}. Аналитика может отражать более старые снимки.`,
      href: "/app/status",
      action: "Проверить",
    });
  }

  if ((queue.dead_letter_count ?? 0) > 0) {
    banners.push({
      id: "dead-letters",
      tone: "bad",
      title: "Есть ошибки обработки",
      detail: `Задач с финальной ошибкой: ${queue.dead_letter_count}. Откройте историю загрузок и повторите при необходимости.`,
      href: "/app/reports",
      action: "История отчётов",
    });
  }

  if ((queue.processing_count ?? 0) > 0 || (queue.pending_count ?? 0) > 0) {
    banners.push({
      id: "queue-active",
      tone: "info",
      title: "Отчёты обрабатываются",
      detail: `В очереди: ${queue.pending_count ?? 0}, обрабатывается: ${queue.processing_count ?? 0}. Дашборд обновится автоматически.`,
      href: "/app/reports",
      action: "Смотреть прогресс",
    });
  }

  const failedReports = reports?.filter((r) => String(r.status).toLowerCase().includes("fail")).length ?? 0;
  if (failedReports > 0) {
    banners.push({
      id: "upload-failed",
      tone: "bad",
      title: "Часть загрузок не обработалась",
      detail: `Ошибок: ${failedReports}. Проверьте формат файла и загрузите повторно.`,
      href: "/app/reports",
      action: "Открыть ошибки",
    });
  }

  if (settings.ai_degraded_alerts && aiOps?.degraded_intelligence_mode) {
    banners.push({
      id: "ai-degraded",
      tone: "warn",
      title: "AI в осторожном режиме",
      detail: "Если данные устарели или идёт пересборка, уверенность рекомендаций снижается. Перед действием проверьте доказательства.",
      href: "/app/ai/recommendations",
      action: "Открыть рекомендации",
    });
  }

  if (settings.stale_data_alerts && (tenantState.includes("stale") || workloadState.includes("degraded"))) {
    banners.push({
      id: "stale-data",
      tone: "warn",
      title: "Данные могут быть неактуальны",
      detail: "Состояние системы указывает на устаревание/деградацию данных. Относитесь к KPI и выводам AI осторожно.",
      href: "/app/status",
      action: "Проверить актуальность",
    });
  }

  const severity = String(health.overall_severity ?? "").toLowerCase();
  if (severity === "critical" || severity === "warning") {
    banners.push({
      id: "health-warning",
      tone: severity === "critical" ? "bad" : "warn",
      title: "Требуется внимание к системе",
      detail: String(health.overall_score ? `Оценка здоровья: ${health.overall_score}.` : "Откройте статус системы."),
      href: "/app/status",
      action: "Подробнее",
    });
  }

  if (banners.length === 0) {
    banners.push({
      id: "all-clear",
      tone: "ok",
      title: "Всё стабильно",
      detail: "Активных инцидентов нет. Загружайте отчёты регулярно, чтобы аналитика оставалась актуальной.",
    });
  }

  return banners;
}

export function TrustBanners() {
  const runtime = useQuery({
    queryKey: ["ops", "runtimeSummary"],
    queryFn: () => api.ops.runtimeSummary(),
    refetchInterval: 30_000,
  });
  const aiOps = useQuery({
    queryKey: ["ai", "ops"],
    queryFn: () => api.ai.operationalStatus(),
    refetchInterval: 30_000,
  });
  const reports = useQuery({
    queryKey: ["reports", "list", 0, 20],
    queryFn: () => api.reports.list(0, 20),
  });

  const banners = collectBanners(
    runtime.data as Record<string, unknown> | undefined,
    aiOps.data as Record<string, unknown> | undefined,
    reports.data,
  );

  const visible = banners.filter((b) => b.id !== "all-clear" || banners.length === 1).slice(0, 4);

  return (
    <div className="space-y-2">
      {visible.map((b) => (
        <Card
          key={b.id}
          className={
            b.tone === "bad"
              ? "border-rose-500/30 bg-rose-500/10 p-3"
              : b.tone === "warn"
                ? "border-amber-500/30 bg-amber-500/10 p-3"
                : b.tone === "ok"
                  ? "border-emerald-500/30 bg-emerald-500/10 p-3"
                  : "border-sky-500/30 bg-sky-500/10 p-3"
          }
        >
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <StatusBadge tone={b.tone}>{b.title}</StatusBadge>
              </div>
              <div className="mt-1 text-xs text-slate-200">{b.detail}</div>
            </div>
            {b.href ? (
              <Link
                to={b.href}
                className="shrink-0 rounded-lg bg-slate-900/50 px-3 py-1.5 text-xs font-medium text-slate-100 hover:bg-slate-800"
              >
                {b.action ?? "Подробнее"}
              </Link>
            ) : null}
          </div>
        </Card>
      ))}
    </div>
  );
}

export function AiTrustNotice() {
  return (
    <Card className="border-slate-700/70 bg-slate-950/40 p-4 text-xs text-slate-300">
      <div className="font-medium text-slate-200">Важное про AI</div>
      <ul className="mt-2 list-disc space-y-1 pl-4">
        <li>Рекомендации AI носят советный характер и не меняют ваши данные автоматически.</li>
        <li>Перед ценами, поставками и рекламой проверьте доказательства и уровень уверенности.</li>
        <li>Если данные устарели или идёт пересборка, AI может работать в «осторожном» режиме.</li>
        <li>Ваши отметки «принято/отклонено» улучшают релевантность, но не отменяют правила governance.</li>
      </ul>
    </Card>
  );
}
