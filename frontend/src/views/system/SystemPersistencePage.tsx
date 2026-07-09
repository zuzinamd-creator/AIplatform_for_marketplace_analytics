import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";

export function SystemPersistencePage() {
  const persistence = useQuery({
    queryKey: ["system", "persistenceStatus"],
    queryFn: () => api.system.persistenceStatus(),
  });

  const p = persistence.data ?? {};

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Persistence</div>
        <div className="text-sm text-ink-secondary">Диагностика хранилища и окружения (platform admin).</div>
      </div>
      <Card className="space-y-2 p-5 text-sm">
        {persistence.isLoading ? <div className="text-ink-muted">Загрузка…</div> : null}
        {persistence.isError ? (
          <div className="text-semantic-danger">Не удалось загрузить persistence status.</div>
        ) : null}
        <div>Environment: {String(p.environment ?? "—")}</div>
        <div>DB: {String(p.db_name ?? "—")} @ {String(p.db_host ?? "—")}</div>
        <div>Persistent storage: {String(p.persistent_storage ?? "—")}</div>
        <div>Reports: {String(p.total_reports ?? "—")}</div>
        <div>Cost rows: {String(p.total_cost_rows ?? "—")}</div>
        <div>AI runs: {String(p.total_ai_runs ?? "—")}</div>
      </Card>
    </div>
  );
}
