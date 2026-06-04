import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { AiTrustNotice } from "../../ui/trust-banners";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";

function plainSeverity(sev?: string) {
  const s = (sev ?? "").toLowerCase();
  if (s === "critical") return "Критично — требуется внимание";
  if (s === "warning") return "Предупреждение — лучше проверить";
  if (s === "healthy") return "Норма";
  return sev ?? "Неизвестно";
}

export function SystemStatusPage() {
  const runtime = useQuery({
    queryKey: ["ops", "runtimeSummary"],
    queryFn: () => api.ops.runtimeSummary(),
  });
  const aiOps = useQuery({
    queryKey: ["ai", "ops"],
    queryFn: () => api.ai.operationalStatus(),
  });

  const r = runtime.data as Record<string, unknown> | undefined;
  const queue = (r?.queue ?? {}) as Record<string, number>;
  const rebuild = (r?.rebuild ?? {}) as Record<string, number>;
  const health = (r?.health ?? {}) as Record<string, unknown>;
  const ai = aiOps.data as Record<string, unknown> | undefined;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Статус системы</div>
        <div className="text-sm text-ink-secondary">
          Простое объяснение обработки загрузок, актуальности данных и готовности AI. Никаких “операторских” действий не требуется.
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card className="p-4">
          <div className="text-xs text-ink-muted">Обработка загрузок</div>
          <div className="mt-2 text-lg font-semibold">
            {queue.pending_count ?? 0} в очереди · {queue.processing_count ?? 0} в работе
          </div>
          <div className="mt-1 text-xs text-ink-muted">
            {queue.dead_letter_count ? `Ошибок: ${queue.dead_letter_count} (нужно проверить)` : "Ошибок нет"}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-ink-muted">Обновление данных</div>
          <div className="mt-2 text-lg font-semibold">
            {rebuild.running ?? 0} выполняется · {rebuild.pending_dispatch ?? 0} в очереди
          </div>
          <div className="mt-1 text-xs text-ink-muted">
            Пока идёт пересборка, KPI могут временно “отставать”. Это нормально после новых загрузок.
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-ink-muted">Готовность AI</div>
          <div className="mt-2 flex items-center gap-2">
            {ai?.degraded_intelligence_mode ? (
              <StatusBadge tone="warn">Осторожный режим</StatusBadge>
            ) : (
              <StatusBadge tone="ok">Норма</StatusBadge>
            )}
          </div>
          <div className="mt-1 text-xs text-ink-muted">
            Успешность: {String(ai?.success_rate ?? "н/д")} · Ожидает подтверждения:{" "}
            {String(ai?.pending_approvals ?? 0)}
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <div className="text-sm font-semibold">Что это значит для продавца</div>
        <div className="mt-3 space-y-2 text-sm text-ink-secondary">
          <p>
            <span className="font-medium text-ink-secondary">Загрузка с ошибкой?</span> Проверьте формат файла и выбор
            маркетплейса, затем загрузите повторно. Дубликаты распознаются автоматически.
          </p>
          <p>
            <span className="font-medium text-ink-secondary">Данные неактуальны?</span> Дождитесь завершения пересборки или
            загрузите более свежие отчёты. При низкой актуальности AI включает “осторожный режим”.
          </p>
          <p>
            <span className="font-medium text-ink-secondary">AI выглядит ошибочным?</span> Откройте объяснимость, сравните
            доказательства и отклоните с причиной. Не действуйте по рекомендациям с низкой уверенностью без проверки.
          </p>
        </div>
        <div className="mt-4 text-xs text-ink-muted">
          Здоровье: {plainSeverity(String(health.overall_severity ?? ""))} · Состояние tenant:{" "}
          {String(r?.tenant_state ?? "н/д")} · Нагрузка: {String(r?.workload_state ?? "н/д")}
        </div>
      </Card>

      <AiTrustNotice />

      <div className="flex flex-wrap gap-2 text-sm">
        <Link to="/app/reports" className="text-brand hover:underline">
          История отчётов
        </Link>
        <Link to="/app/ai/recommendations" className="text-brand hover:underline">
          Рекомендации
        </Link>
        <Link to="/app/support" className="text-brand hover:underline">
          Поддержка и диагностика
        </Link>
      </div>
    </div>
  );
}
