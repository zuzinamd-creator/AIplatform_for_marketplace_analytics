import { NavLink, Outlet } from "react-router-dom";

import { cx } from "../ui/cx";
import { ANALYTICS_TABS } from "./analytics-tabs";

export function AnalyticsShell() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Аналитика</h1>
        <p className="page-subtitle">
          Единый центр финансовой аналитики: обзор бизнеса, сравнение периодов, экономика SKU и качество данных о
          себестоимости.
        </p>
      </div>

      <nav aria-label="Вкладки аналитики" className="flex flex-wrap gap-1 border-b border-surface-subtle">
        {ANALYTICS_TABS.map((tab) => (
          <NavLink
            key={tab.id}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              cx(
                "rounded-t-lg px-4 py-2.5 text-sm font-medium transition",
                isActive ? "analytics-tab-active" : "analytics-tab-idle",
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  );
}
