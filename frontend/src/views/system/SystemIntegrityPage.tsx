import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";

export function SystemIntegrityPage() {
  const integrity = useQuery({
    queryKey: ["system", "dataIntegrity"],
    queryFn: () => api.system.dataIntegrity(),
  });

  const d = integrity.data ?? {};

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Целостность данных</div>
        <div className="text-sm text-ink-secondary">Проверка согласованности отчётов и очереди (platform admin).</div>
      </div>
      <Card className="space-y-3 p-5 text-sm">
        {integrity.isLoading ? <div className="text-ink-muted">Загрузка…</div> : null}
        {integrity.isError ? (
          <div className="text-semantic-danger">Не удалось загрузить data integrity.</div>
        ) : null}
        <div className="flex items-center gap-2">
          <span>Healthy:</span>
          {d.healthy ? <StatusBadge tone="ok">OK</StatusBadge> : <StatusBadge tone="warn">Issues</StatusBadge>}
        </div>
        <div>Reports: {String(d.total_reports ?? "—")}</div>
        <div>Reports without job: {String(d.reports_without_job ?? "—")}</div>
        <div>Orphan ETL jobs: {String(d.orphan_etl_jobs ?? "—")}</div>
      </Card>
    </div>
  );
}
