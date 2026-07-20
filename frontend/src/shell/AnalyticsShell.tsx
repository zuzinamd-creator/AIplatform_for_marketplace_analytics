import { NavLink, Outlet, useLocation } from "react-router-dom";

import { cx } from "../ui/cx";
import { ANALYTICS_OVERVIEW_ROUTE, ANALYTICS_TABS } from "./analytics-tabs";
import { AnalyticsPeriodProvider } from "./analytics-period-context";

export function AnalyticsShell() {
  const { pathname } = useLocation();
  const isOverview =
    pathname === ANALYTICS_OVERVIEW_ROUTE || pathname === `${ANALYTICS_OVERVIEW_ROUTE}/`;

  return (
    <AnalyticsPeriodProvider>
      <div className={cx("space-y-4", isOverview && "space-y-3")}>
        <div>
          <h1 className={isOverview ? "page-title-compact" : "page-title"}>Аналитика</h1>
          {!isOverview ? (
            <p className="page-subtitle">
              Сравнение периодов, экономика SKU и качество данных о себестоимости.
            </p>
          ) : null}
        </div>

        <nav aria-label="Вкладки аналитики" className="flex flex-wrap gap-1 border-b border-surface-subtle">
          {ANALYTICS_TABS.map((tab) => (
            <NavLink
              key={tab.id}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                cx(
                  "rounded-t-lg px-4 py-2 text-sm font-medium transition",
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
    </AnalyticsPeriodProvider>
  );
}
