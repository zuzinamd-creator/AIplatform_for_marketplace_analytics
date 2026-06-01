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
    <div className="min-h-screen">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex flex-col gap-6 md:flex-row">
          <aside className="md:w-64">
            <Card className="p-4 shadow-soft">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold">{profile.workspace_name}</div>
                  <div className="text-xs text-slate-300">Аналитика маркетплейсов</div>
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

              <div className="mt-3 rounded-lg bg-slate-900/60 px-3 py-2">
                <div className="text-xs text-slate-300">Вы вошли как</div>
                <div className="truncate text-sm">{user?.email ?? "…"}</div>
              </div>
              <div className="mt-2 rounded-lg border border-slate-800/70 bg-slate-950/30 px-3 py-2">
                <div className="text-[10px] uppercase tracking-wide text-slate-400">Окружение</div>
                <div className="mt-0.5 flex items-center justify-between gap-2 text-xs">
                  <span
                    className={
                      envMode === "INTEGRATION"
                        ? "text-rose-200"
                        : envMode === "MAIN"
                          ? "text-emerald-200"
                          : "text-amber-200"
                    }
                  >
                    {envLabel}
                  </span>
                  <span className="truncate text-slate-500">{apiBase.replace(/^https?:\/\//, "")}</span>
                </div>
                <div className="mt-1 text-[11px] text-slate-500">
                  База: {dbName || "—"} @ {dbHost || "—"} · Хранилище:{" "}
                  {persistent ? <span className="text-emerald-200">persistent</span> : <span className="text-rose-200">ephemeral</span>}
                </div>
                {!persistent ? (
                  <div className="mt-1 text-[11px] text-rose-200/90">
                    В тестовом/локальном окружении данные могут удаляться (reset/volume). Для рабочего режима используйте MAIN + cloud DB.
                  </div>
                ) : null}
              </div>
              {!isOnboardingDone() ? (
                <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                  Завершите <span className="font-medium">настройку</span>, чтобы аналитика стала полезнее.
                </div>
              ) : null}

              <nav className="mt-4 flex flex-col gap-1" aria-label="Main navigation">
                {nav.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        cx(
                          "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition",
                          isActive
                            ? "bg-sky-500/15 text-sky-200"
                            : "text-slate-200 hover:bg-slate-800/60",
                        )
                      }
                    >
                      <Icon className="h-4 w-4" />
                      <span className="flex-1">{item.label}</span>
                      {item.maturity === "beta" ? (
                        <span className="text-[10px] text-amber-300">бета</span>
                      ) : null}
                    </NavLink>
                  );
                })}
              </nav>
            </Card>
          </aside>

          <main className="min-w-0 flex-1 space-y-4">
            <TrustBanners />
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
