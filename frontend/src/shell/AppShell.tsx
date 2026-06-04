import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Activity,
  Bot,
  Database,
  Gauge,
  LayoutDashboard,
  LifeBuoy,
  LineChart,
  LogOut,
  Package,
  Settings,
  Settings2,
  Shield,
  Upload,
} from "lucide-react";
import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../state/auth";
import { isOnboardingDone, loadWorkspaceProfile } from "../state/onboarding";
import { isMvpMode, loadSettings } from "../state/settings";
import { api } from "../state/http";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { cx } from "../ui/cx";
import { TrustBanners } from "../ui/trust-banners";

type NavItem = {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  maturity?: "stable" | "beta" | "internal";
};

const allNav: NavItem[] = [
  { to: "/app/onboarding", label: "Настройка", icon: Settings2, maturity: "stable" },
  { to: "/app/dashboard", label: "Панель", icon: LayoutDashboard, maturity: "stable" },
  { to: "/app/today", label: "Сегодня", icon: Gauge, maturity: "stable" },
  { to: "/app/status", label: "Статус системы", icon: Shield, maturity: "stable" },
  { to: "/app/reports", label: "Отчёты", icon: Database, maturity: "stable" },
  { to: "/app/reports/upload", label: "Загрузка", icon: Upload, maturity: "stable" },
  { to: "/app/costs", label: "Себестоимость", icon: Database, maturity: "stable" },
  { to: "/app/finance/costs", label: "Покрытие затрат", icon: Database, maturity: "stable" },
  { to: "/app/finance/reconciliation", label: "Сверка выплат", icon: Shield, maturity: "stable" },
  { to: "/app/economics", label: "Экономика SKU", icon: LineChart, maturity: "stable" },
  { to: "/app/economics/inventory", label: "Склад и оборот", icon: Package, maturity: "stable" },
  { to: "/app/ai/recommendations", label: "ИИ-помощник", icon: Bot, maturity: "stable" },
  { to: "/app/ai/today", label: "Фокус на сегодня", icon: Bot, maturity: "stable" },
  { to: "/app/ai/digest", label: "Дайджест ИИ", icon: Bot, maturity: "beta" },
  { to: "/app/ai/usage", label: "Расход ИИ", icon: Bot, maturity: "beta" },
  { to: "/app/ai/runs", label: "История ИИ", icon: Bot, maturity: "beta" },
  { to: "/app/ops/queue", label: "Операции", icon: Activity, maturity: "internal" },
  { to: "/app/ops/runtime/summary", label: "Рантайм", icon: Gauge, maturity: "internal" },
  { to: "/app/settings", label: "Настройки", icon: Settings, maturity: "stable" },
  { to: "/app/support", label: "Поддержка", icon: LifeBuoy, maturity: "stable" },
];

function filterNav(): NavItem[] {
  const settings = loadSettings();
  const mvp = isMvpMode();
  return allNav.filter((item) => {
    if (item.maturity === "internal" && mvp && !settings.show_internal_ops) return false;
    if (item.maturity === "beta" && settings.product_mode === "mvp" && !settings.show_internal_ops) return false;
    return true;
  });
}

export function AppShell() {
  const { user, refreshMe, signOut } = useAuth();
  const navigate = useNavigate();
  const profile = loadWorkspaceProfile();
  const nav = useMemo(() => filterNav(), []);
  const apiBase = String(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080");
  const persistence = useQuery({
    queryKey: ["system", "persistenceStatus"],
    queryFn: () => api.system.persistenceStatus(),
    refetchInterval: 60_000,
  });
  const p = persistence.data as any;
  const envMode = String(p?.environment ?? "");
  const dbName = String(p?.db_name ?? "");
  const dbHost = String(p?.db_host ?? "");
  const persistent = Boolean(p?.persistent_storage);
  const envLabel = envMode === "INTEGRATION" ? "ТЕСТОВОЕ ОКРУЖЕНИЕ" : envMode === "MAIN" ? "ОСНОВНОЕ РАБОЧЕЕ ОКРУЖЕНИЕ" : "ЛОКАЛЬНАЯ РАЗРАБОТКА";

  useEffect(() => {
    void refreshMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-surface-muted">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 lg:px-8">
        <div className="flex flex-col gap-8 md:flex-row md:items-start">
          <aside className="md:w-64 md:shrink-0">
            <Card className="sticky top-6 p-5 shadow-soft">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold text-ink">{profile.workspace_name}</div>
                  <div className="text-xs text-ink-muted">Аналитика маркетплейсов</div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    signOut();
                    navigate("/login");
                  }}
                  aria-label="Выйти"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>

              <div className="mt-4 rounded-xl bg-surface-inset px-3 py-2.5 ring-1 ring-surface-subtle/80">
                <div className="text-xs text-ink-muted">Вы вошли как</div>
                <div className="truncate text-sm font-medium text-ink">{user?.email ?? "…"}</div>
              </div>
              <div className="mt-3 rounded-xl border border-surface-subtle bg-surface-inset/60 px-3 py-2.5">
                <div className="text-[10px] font-medium uppercase tracking-wide text-ink-faint">Окружение</div>
                <div className="mt-1 flex items-center justify-between gap-2 text-xs">
                  <span
                    className={
                      envMode === "INTEGRATION"
                        ? "font-medium text-semantic-danger"
                        : envMode === "MAIN"
                          ? "font-medium text-semantic-success"
                          : "font-medium text-semantic-warn"
                    }
                  >
                    {envLabel}
                  </span>
                  <span className="truncate text-ink-faint">{apiBase.replace(/^https?:\/\//, "")}</span>
                </div>
                <div className="mt-1 text-[11px] leading-relaxed text-ink-muted">
                  База: {dbName || "—"} @ {dbHost || "—"} · Хранилище:{" "}
                  {persistent ? <span className="text-semantic-success">persistent</span> : <span className="text-semantic-danger">ephemeral</span>}
                </div>
                {!persistent ? (
                  <div className="mt-1.5 text-[11px] leading-relaxed text-semantic-danger">
                    В тестовом/локальном окружении данные могут удаляться (reset/volume). Для рабочего режима используйте MAIN + cloud DB.
                  </div>
                ) : null}
              </div>
              {!isOnboardingDone() ? (
                <div className="mt-3 rounded-xl border border-amber-200 bg-semantic-warn-bg px-3 py-2.5 text-xs text-semantic-warn">
                  Завершите <span className="font-medium">настройку</span>, чтобы аналитика стала полезнее.
                </div>
              ) : null}

              <nav className="mt-5 flex flex-col gap-0.5" aria-label="Main navigation">
                {nav.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        cx(
                          "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition",
                          isActive ? "nav-item-active" : "nav-item-idle",
                        )
                      }
                    >
                      <Icon className="h-4 w-4" />
                      <span className="flex-1">{item.label}</span>
                      {item.maturity === "beta" ? (
                        <span className="text-[10px] font-medium text-semantic-warn">бета</span>
                      ) : null}
                    </NavLink>
                  );
                })}
              </nav>
            </Card>
          </aside>

          <main className="min-w-0 flex-1 space-y-6 pb-10">
            <TrustBanners />
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
