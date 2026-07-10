import { BarChart3, LayoutDashboard, LineChart, Shield } from "lucide-react";
import { Link } from "react-router-dom";

import { COST_COVERAGE_ROUTE } from "../../state/profit-trust";
import { Card } from "../../ui/card";

const ENTRIES = [
  {
    to: "/app/dashboard",
    title: "Обзор бизнеса",
    description: "Что происходит сейчас: KPI, тренды, риски и операционная ситуация за период.",
    icon: LayoutDashboard,
  },
  {
    to: "/app/analytics/weekly",
    title: "Сравнение периодов",
    description: "Почему изменились показатели: дельты выручки, прибыли, маржи, ABC и складские риски.",
    icon: BarChart3,
  },
  {
    to: "/app/economics",
    title: "Экономика SKU",
    description: "Прибыльность по товарам: маржа, затраты и утечки прибыли на уровне SKU.",
    icon: LineChart,
  },
  {
    to: COST_COVERAGE_ROUTE,
    title: "Покрытие себестоимости",
    description: "Доля SKU с загруженной себестоимостью — основа доверия к прибыли и марже.",
    icon: Shield,
  },
] as const;

export function AnalyticsHubPage() {
  return (
    <div className="page-shell">
      <div>
        <h1 className="page-title">Аналитика</h1>
        <p className="page-subtitle">
          Единая точка входа в финансовую аналитику: обзор, сравнение периодов, экономика SKU и качество данных.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {ENTRIES.map((entry) => {
          const Icon = entry.icon;
          return (
            <Link key={entry.to} to={entry.to} className="block no-underline">
              <Card className="h-full p-5 transition-colors hover:border-brand/40 hover:bg-surface-elevated">
                <div className="flex items-start gap-3">
                  <div className="rounded-lg bg-surface-subtle p-2 text-brand">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-ink">{entry.title}</div>
                    <p className="mt-2 text-xs leading-relaxed text-ink-secondary">{entry.description}</p>
                    <span className="link-muted mt-3 inline-block text-xs">Открыть →</span>
                  </div>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>

      <p className="text-xs text-ink-muted">
        Рекомендуемый путь: обзор → сравнение периодов → экономика SKU → рекомендации ИИ. При низком покрытии себестоимости начните с
        загрузки COGS.
      </p>
    </div>
  );
}
