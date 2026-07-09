import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { useMemo } from "react";

import { useAuth } from "../state/auth";
import { isOnboardingDone, loadWorkspaceProfile } from "../state/onboarding";
import { isPlatformAdmin } from "../state/userRoles";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { cx } from "../ui/cx";
import { TrustBanners } from "../ui/trust-banners";
import { buildNavSections } from "./nav";

export function AppShell() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const profile = loadWorkspaceProfile();
  const navSections = useMemo(() => buildNavSections(user), [user]);
  const admin = isPlatformAdmin(user);

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
                {user?.role ? (
                  <div className="mt-1 text-[11px] uppercase tracking-wide text-ink-faint">{user.role}</div>
                ) : null}
              </div>

              {!isOnboardingDone() && !admin ? (
                <div className="mt-3 rounded-xl border border-amber-200 bg-semantic-warn-bg px-3 py-2.5 text-xs text-semantic-warn">
                  Завершите <span className="font-medium">настройку</span>, чтобы аналитика стала полезнее.
                </div>
              ) : null}

              <nav className="mt-5 flex flex-col gap-4" aria-label="Main navigation">
                {navSections.map((section) => (
                  <div key={section.id}>
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wide text-ink-faint">
                      {section.label}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      {section.items.map((item) => {
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
                          </NavLink>
                        );
                      })}
                    </div>
                  </div>
                ))}
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
