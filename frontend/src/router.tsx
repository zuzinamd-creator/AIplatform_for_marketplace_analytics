import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { ErrorBoundary } from "react-error-boundary";

import { AppShell } from "./shell/AppShell";
import { RequireAuth } from "./state/auth";
import { RouteError } from "./ui/route-error";

import { LoginPage } from "./views/auth/LoginPage";
import { RegisterPage } from "./views/auth/RegisterPage";
import { ForgotPasswordPage } from "./views/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "./views/auth/ResetPasswordPage";

import { DashboardPage } from "./views/dashboard/DashboardPage";
import { OnboardingPage } from "./views/onboarding/OnboardingPage";
import { UploadReportPage } from "./views/reports/UploadReportPage";
import { ReportsPage } from "./views/reports/ReportsPage";
import { ReportDetailPage } from "./views/reports/ReportDetailPage";
import { CostsPage } from "./views/costs/CostsPage";
import { SettingsPage } from "./views/settings/SettingsPage";
import { SupportPage } from "./views/support/SupportPage";
import { SystemStatusPage } from "./views/status/SystemStatusPage";

import { RecommendationsPage } from "./views/ai/RecommendationsPage";
import { RecommendationDetailPage } from "./views/ai/RecommendationDetailPage";
import { AiRunsPage } from "./views/ai/AiRunsPage";
import { AiRunDetailPage } from "./views/ai/AiRunDetailPage";
import { AiOperationalStatusPage } from "./views/ai/AiOperationalStatusPage";
import { AiDigestPage } from "./views/ai/AiDigestPage";
import { AiTodayPage } from "./views/ai/AiTodayPage";
import { AiUsagePage } from "./views/ai/AiUsagePage";
import { TodayPage } from "./views/today/TodayPage";

import { QueuePage } from "./views/ops/QueuePage";
import { DeadLettersPage } from "./views/ops/DeadLettersPage";
import { RebuildsPage } from "./views/ops/RebuildsPage";
import { DriftChecksPage } from "./views/ops/DriftChecksPage";
import { AnomaliesPage } from "./views/ops/AnomaliesPage";
import { RuntimeHealthPage } from "./views/ops/RuntimeHealthPage";
import { RuntimeSummaryPage } from "./views/ops/RuntimeSummaryPage";
import { SemanticsStatusPage } from "./views/ops/SemanticsStatusPage";
import { ReconciliationPage } from "./views/finance/ReconciliationPage";
import { EconomicsPage } from "./views/economics/EconomicsPage";
import { SkuDrilldownPage } from "./views/economics/SkuDrilldownPage";
import { InventoryEconomicsPage } from "./views/economics/InventoryEconomicsPage";

const withBoundary = (node: React.ReactNode) => (
  <ErrorBoundary fallbackRender={({ error }) => <RouteError error={error} />}>
    {node}
  </ErrorBoundary>
);

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/app" replace /> },
  { path: "/login", element: withBoundary(<LoginPage />) },
  { path: "/register", element: withBoundary(<RegisterPage />) },
  { path: "/forgot-password", element: withBoundary(<ForgotPasswordPage />) },
  { path: "/reset-password", element: withBoundary(<ResetPasswordPage />) },
  {
    path: "/app",
    element: withBoundary(
      <RequireAuth>
        <AppShell />
      </RequireAuth>,
    ),
    children: [
      { index: true, element: <Navigate to="dashboard" replace /> },
      { path: "onboarding", element: withBoundary(<OnboardingPage />) },
      { path: "dashboard", element: withBoundary(<DashboardPage />) },
      { path: "status", element: withBoundary(<SystemStatusPage />) },
      { path: "settings", element: withBoundary(<SettingsPage />) },
      { path: "support", element: withBoundary(<SupportPage />) },
      { path: "reports", element: withBoundary(<ReportsPage />) },
      { path: "reports/upload", element: withBoundary(<UploadReportPage />) },
      { path: "reports/:reportId", element: withBoundary(<ReportDetailPage />) },
      { path: "costs", element: withBoundary(<CostsPage />) },
      { path: "finance/costs", element: <Navigate to="/app/costs" replace /> },
      { path: "finance/reconciliation", element: withBoundary(<ReconciliationPage />) },
      { path: "economics", element: withBoundary(<EconomicsPage />) },
      { path: "economics/sku/:sku", element: withBoundary(<SkuDrilldownPage />) },
      { path: "economics/inventory", element: withBoundary(<InventoryEconomicsPage />) },

      { path: "ai/recommendations", element: withBoundary(<RecommendationsPage />) },
      { path: "ai/recommendations/:recommendationId", element: withBoundary(<RecommendationDetailPage />) },
      { path: "ai/runs", element: withBoundary(<AiRunsPage />) },
      { path: "ai/runs/:runId", element: withBoundary(<AiRunDetailPage />) },
      { path: "ai/ops", element: withBoundary(<AiOperationalStatusPage />) },
      { path: "ai/today", element: withBoundary(<AiTodayPage />) },
      { path: "today", element: withBoundary(<TodayPage />) },
      { path: "ai/digest", element: withBoundary(<AiDigestPage />) },
      { path: "ai/usage", element: withBoundary(<AiUsagePage />) },

      { path: "ops/queue", element: withBoundary(<QueuePage />) },
      { path: "ops/dead-letters", element: withBoundary(<DeadLettersPage />) },
      { path: "ops/rebuilds", element: withBoundary(<RebuildsPage />) },
      { path: "ops/drift-checks", element: withBoundary(<DriftChecksPage />) },
      { path: "ops/anomalies", element: withBoundary(<AnomaliesPage />) },
      { path: "ops/runtime/health", element: withBoundary(<RuntimeHealthPage />) },
      { path: "ops/runtime/summary", element: withBoundary(<RuntimeSummaryPage />) },
      { path: "ops/semantics", element: withBoundary(<SemanticsStatusPage />) },
    ],
  },
  { path: "*", element: <RouteError status={404} title="Not found" /> },
]);

