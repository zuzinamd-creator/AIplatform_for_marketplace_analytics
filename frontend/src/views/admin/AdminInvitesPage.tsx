import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, formatApiError } from "../../state/http";
import type { AdminInviteCreateResponse, InviteStatus } from "../../state/types-admin";
import { Button } from "../../ui/button";
import { Card } from "../../ui/card";
import { Input, Label } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";
import { toast } from "../../ui/toast";

function fmtDate(iso: string): string {
  const d = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return "—";
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y}`;
}

function statusTone(status: InviteStatus): "ok" | "info" | "warn" | "bad" {
  switch (status) {
    case "pending":
      return "info";
    case "used":
      return "ok";
    case "expired":
      return "warn";
    case "revoked":
      return "bad";
  }
}

export function AdminInvitesPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [email, setEmail] = useState("");
  const [ttlHours, setTtlHours] = useState("72");
  const [createdInvite, setCreatedInvite] = useState<AdminInviteCreateResponse | null>(null);

  const q = useQuery({
    queryKey: ["admin", "invites", 0, 50],
    queryFn: () => api.admin.listInvites(0, 50),
  });

  const createMutation = useMutation({
    mutationFn: () => api.admin.createInvite(email.trim(), Number(ttlHours) || 72),
    onSuccess: (data) => {
      setCreatedInvite(data);
      void queryClient.invalidateQueries({ queryKey: ["admin", "invites"] });
      toast("Приглашение создано", "Скопируйте ссылку и передайте пользователю.");
    },
    onError: (err) => {
      toast("Не удалось создать приглашение", formatApiError(err));
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (inviteId: string) => api.admin.revokeInvite(inviteId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "invites"] });
      toast("Приглашение отозвано", "");
    },
    onError: (err) => {
      toast("Не удалось отозвать приглашение", formatApiError(err));
    },
  });

  const items = q.data?.items ?? [];
  const total = q.data?.page.total ?? 0;

  const copyLink = async (link: string) => {
    try {
      await navigator.clipboard.writeText(link);
      toast("Ссылка скопирована", "");
    } catch {
      toast("Не удалось скопировать", link);
    }
  };

  const closeCreateModal = () => {
    setShowCreate(false);
    setEmail("");
    setTtlHours("72");
    setCreatedInvite(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-2xl font-semibold">Приглашения</div>
          <div className="text-sm text-ink-secondary">Управление приглашениями пользователей</div>
        </div>
        <Button type="button" onClick={() => setShowCreate(true)}>
          Создать приглашение
        </Button>
      </div>

      <Card className="overflow-hidden p-0">
        {q.isLoading ? (
          <div className="p-5 text-sm text-ink-secondary">Загрузка…</div>
        ) : q.isError ? (
          <div className="p-5 text-sm text-semantic-danger">Не удалось загрузить список приглашений.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-surface-inset text-left text-xs uppercase tracking-wide text-ink-faint">
                <tr>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">Expires</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr className="border-t border-surface-subtle">
                    <td colSpan={5} className="px-4 py-8 text-center text-ink-muted">
                      Приглашений пока нет
                    </td>
                  </tr>
                ) : (
                  items.map((row) => (
                    <tr key={row.id} className="border-t border-surface-subtle">
                      <td className="px-4 py-3 font-medium text-ink">{row.email}</td>
                      <td className="px-4 py-3">
                        <StatusBadge tone={statusTone(row.status)}>{row.status}</StatusBadge>
                      </td>
                      <td className="px-4 py-3 text-ink-secondary">{fmtDate(row.created_at)}</td>
                      <td className="px-4 py-3 text-ink-secondary">{fmtDate(row.expires_at)}</td>
                      <td className="px-4 py-3">
                        {row.status === "pending" ? (
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            disabled={revokeMutation.isPending}
                            onClick={() => revokeMutation.mutate(row.id)}
                          >
                            Отозвать
                          </Button>
                        ) : (
                          <span className="text-ink-muted">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        <div className="border-t border-surface-subtle px-4 py-3 text-xs text-ink-muted">Всего: {total}</div>
      </Card>

      {showCreate ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-lg p-6 shadow-soft">
            <div className="text-lg font-semibold">Создать приглашение</div>
            {createdInvite ? (
              <div className="mt-4 space-y-4">
                <p className="text-sm text-ink-secondary">
                  Приглашение для <span className="font-medium text-ink">{createdInvite.email}</span> создано.
                </p>
                <div className="space-y-1.5">
                  <Label>Invite link</Label>
                  <Input readOnly value={createdInvite.invite_link} />
                </div>
                <div className="flex gap-2">
                  <Button type="button" onClick={() => copyLink(createdInvite.invite_link)}>
                    Copy
                  </Button>
                  <Button type="button" variant="secondary" onClick={closeCreateModal}>
                    Закрыть
                  </Button>
                </div>
              </div>
            ) : (
              <form
                className="mt-4 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  createMutation.mutate();
                }}
              >
                <div className="space-y-1.5">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="off"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>TTL (часы)</Label>
                  <Input
                    type="number"
                    min={1}
                    max={720}
                    value={ttlHours}
                    onChange={(e) => setTtlHours(e.target.value)}
                    required
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Создание…" : "Создать"}
                  </Button>
                  <Button type="button" variant="secondary" onClick={closeCreateModal}>
                    Отмена
                  </Button>
                </div>
              </form>
            )}
          </Card>
        </div>
      ) : null}
    </div>
  );
}
