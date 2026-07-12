import { Navigate, useLocation } from "react-router-dom";

import { ANALYTICS_OVERVIEW_ROUTE } from "./analytics-tabs";

/** Soft redirect: legacy /app/dashboard bookmarks resolve to Analytics Hub overview. */
export function DashboardRedirect() {
  const location = useLocation();
  const target = `${ANALYTICS_OVERVIEW_ROUTE}${location.search}${location.hash}`;
  return <Navigate to={target} replace />;
}
