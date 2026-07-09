import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";

function fmtDate(iso: string): string {
  const d = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return "—";
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y}`;
}

export function AdminUsersPage() {
  const q = useQuery({
    queryKey: ["admin", "users", 0, 50],
    queryFn: () => api.admin.listUsers(0, 50),
  });

  const items = q.data?.items ?? [];
  const total = q.data?.page.total ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Пользователи</div>
        <div className="text-sm text-ink-secondary">
          Read-only список учётных записей платформы. Редактирование недоступно в этом релизе.
        </div>
      </div>

      <Card className="overflow-hidden p-0">
        {q.isLoading ? (
          <div className="p-5 text-sm text-ink-secondary">Загрузка…</div>
        ) : q.isError ? (
          <div className="p-5 text-sm text-semantic-danger">Не удалось загрузить список пользователей.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-surface-inset text-left text-xs uppercase tracking-wide text-ink-faint">
                <tr>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Role</th>
                  <th className="px-4 py-3 font-medium">Active</th>
                  <th className="px-4 py-3 font-medium">Registered</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.email} className="border-t border-surface-subtle">
                    <td className="px-4 py-3 font-medium text-ink">{row.email}</td>
                    <td className="px-4 py-3">
                      <StatusBadge tone={row.role === "platform_admin" ? "info" : "ok"}>
                        {row.role}
                      </StatusBadge>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge tone={row.is_active ? "ok" : "bad"}>
                        {row.is_active ? "yes" : "no"}
                      </StatusBadge>
                    </td>
                    <td className="px-4 py-3 text-ink-secondary">{fmtDate(row.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="border-t border-surface-subtle px-4 py-3 text-xs text-ink-muted">
          Всего: {total}
        </div>
      </Card>
    </div>
  );
}
