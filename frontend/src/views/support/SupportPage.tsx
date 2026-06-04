import { useAuth } from "../../state/auth";
import { loadNotifications, markAllRead, markRead } from "../../state/notifications";
import { loadSettings } from "../../state/settings";
import { loadUsage } from "../../state/usage";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { StatusBadge } from "../../ui/status-badge";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

export function SupportPage() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState(() => loadNotifications());
  const usage = useMemo(() => loadUsage().slice(0, 30), []);
  const profile = loadWorkspaceProfile();
  const settings = loadSettings();

  const refreshNotifs = () => setNotifications(loadNotifications());

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Поддержка и диагностика</div>
        <div className="text-sm text-ink-secondary">
          Информация для обращения в поддержку. Страница доступна даже в MVP, чтобы помогать в контролируемом продакшн‑использовании.
        </div>
      </div>

      <Card className="p-5">
        <div className="text-sm font-semibold">Контекст аккаунта</div>
        <dl className="mt-3 grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
          <div>
            <dt className="text-xs text-ink-muted">Email</dt>
            <dd>{user?.email ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">Tenant ID</dt>
            <dd className="font-mono text-xs">{user?.id ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">Рабочее пространство</dt>
            <dd>{profile.workspace_name}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">Режим продукта</dt>
            <dd>
              <StatusBadge tone="info">{settings.product_mode}</StatusBadge>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">API base</dt>
            <dd className="font-mono text-xs">{import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080"}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">Версия фронтенда</dt>
            <dd className="font-mono text-xs">UX-3 MVP</dd>
          </div>
        </dl>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Уведомления</div>
          <Button variant="ghost" size="sm" onClick={() => { markAllRead(); refreshNotifs(); }}>
            Отметить всё прочитанным
          </Button>
        </div>
        {notifications.length === 0 ? (
          <div className="mt-3 text-sm text-ink-muted">Уведомлений пока нет.</div>
        ) : (
          <ul className="mt-3 space-y-2">
            {notifications.slice(0, 15).map((n) => (
              <li
                key={n.id}
                className={`rounded-lg border border-surface-subtle p-3 text-sm ${n.read ? "opacity-60" : ""}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <StatusBadge tone={n.tone}>{n.title}</StatusBadge>
                  <span className="text-[10px] text-ink0">{n.created_at.slice(0, 19)}</span>
                </div>
                {n.detail ? <div className="mt-1 text-xs text-ink-secondary">{n.detail}</div> : null}
                <div className="mt-2 flex gap-2">
                  {!n.read ? (
                    <button
                      type="button"
                      className="text-xs text-brand hover:underline"
                      onClick={() => { markRead(n.id); refreshNotifs(); }}
                    >
                      Отметить прочитанным
                    </button>
                  ) : null}
                  {n.href ? (
                    <Link to={n.href} className="text-xs text-brand hover:underline">
                      Открыть
                    </Link>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="p-5">
        <div className="text-sm font-semibold">Недавняя активность (локально)</div>
        <div className="mt-1 text-xs text-ink-muted">События usage сохраняются в этом браузере для диагностики MVP.</div>
        {usage.length === 0 ? (
          <div className="mt-3 text-sm text-ink-muted">Активность пока не зафиксирована.</div>
        ) : (
          <pre className="mt-3 max-h-64 overflow-auto text-[11px] text-ink-secondary">
            {JSON.stringify(usage, null, 2)}
          </pre>
        )}
      </Card>

      <Card className="p-5 text-xs text-ink-muted">
        При обращении в поддержку укажите: tenant ID, примерное время проблемы, имя файла отчёта (если связано с загрузкой)
        и скрин страницы «Статус системы».
      </Card>
    </div>
  );
}
