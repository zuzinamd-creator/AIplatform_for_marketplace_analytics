import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bot,
  Database,
  Gauge,
  LayoutDashboard,
  LifeBuoy,
  LineChart,
  BarChart3,
  Mail,
  Package,
  Server,
  Settings,
  Settings2,
  Shield,
  Upload,
  Users,
} from "lucide-react";

import { isOnboardingDone } from "../state/onboarding";
import { isPlatformAdmin } from "../state/userRoles";
import type { UserResponse } from "../state/types";

export type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
};

export type NavSection = {
  id: string;
  label: string;
  items: NavItem[];
};

const overviewItems: NavItem[] = [
  { to: "/app/analytics", label: "Панель", icon: LayoutDashboard },
  { to: "/app/today", label: "Сегодня", icon: Gauge },
];

const analyticsItems: NavItem[] = [
  { to: "/app/analytics/weekly", label: "Сравнение периодов", icon: BarChart3 },
  { to: "/app/analytics/economics", label: "Экономика SKU", icon: LineChart },
  { to: "/app/economics/inventory", label: "Склад и оборот", icon: Package },
  { to: "/app/finance/reconciliation", label: "Сверка выплат", icon: Shield },
];

const dataItems: NavItem[] = [
  { to: "/app/reports/upload", label: "Загрузка отчёта", icon: Upload },
  { to: "/app/reports", label: "Отчёты", icon: Database },
  { to: "/app/costs", label: "Себестоимость", icon: Database },
  { to: "/app/analytics/cost-coverage", label: "Покрытие себестоимости", icon: Shield },
];

const actionsItems: NavItem[] = [
  { to: "/app/ai/recommendations", label: "ИИ-помощник", icon: Bot },
  { to: "/app/ai/digest", label: "Сводка ИИ", icon: Bot },
];

const accountItemsAll: NavItem[] = [
  { to: "/app/onboarding", label: "Настройка", icon: Settings2 },
  { to: "/app/settings", label: "Настройки", icon: Settings },
  { to: "/app/support", label: "Поддержка", icon: LifeBuoy },
];

const administrationItems: NavItem[] = [
  { to: "/app/admin/users", label: "Пользователи", icon: Users },
  { to: "/app/admin/invites", label: "Приглашения", icon: Mail },
];

const operationsItems: NavItem[] = [
  { to: "/app/ops/queue", label: "Очередь", icon: Activity },
  { to: "/app/ops/dead-letters", label: "Dead letters", icon: Activity },
  { to: "/app/ops/rebuilds", label: "Пересборки", icon: Activity },
  { to: "/app/ops/drift-checks", label: "Drift checks", icon: Activity },
  { to: "/app/ops/anomalies", label: "Аномалии", icon: Activity },
  { to: "/app/ops/runtime/health", label: "Рантайм health", icon: Gauge },
  { to: "/app/ops/runtime/summary", label: "Рантайм summary", icon: Gauge },
  { to: "/app/ops/semantics", label: "Семантика", icon: Shield },
];

const systemItems: NavItem[] = [
  { to: "/app/system/status", label: "Статус системы", icon: Server },
  { to: "/app/system/persistence", label: "Persistence", icon: Server },
  { to: "/app/system/integrity", label: "Целостность данных", icon: Server },
];

function buildAccountItems(): NavItem[] {
  if (isOnboardingDone()) {
    return accountItemsAll.filter((item) => item.to !== "/app/onboarding");
  }
  return accountItemsAll;
}

function buildSellerSections(): NavSection[] {
  return [
    { id: "overview", label: "Обзор", items: overviewItems },
    { id: "analytics", label: "Аналитика", items: analyticsItems },
    { id: "data", label: "Данные", items: dataItems },
    { id: "actions", label: "Действия", items: actionsItems },
    { id: "account", label: "Аккаунт", items: buildAccountItems() },
  ];
}

const adminSections: NavSection[] = [
  { id: "administration", label: "Администрирование", items: administrationItems },
  { id: "operations", label: "Operations", items: operationsItems },
  { id: "system", label: "System", items: systemItems },
];

export function buildNavSections(user: UserResponse | null | undefined): NavSection[] {
  const sellerSections = buildSellerSections();
  if (isPlatformAdmin(user)) {
    return [...sellerSections, ...adminSections];
  }
  return sellerSections;
}

/** All canonical seller nav targets — for duplicate-URL audits in tests. */
export function sellerNavTargets(): string[] {
  return buildSellerSections().flatMap((section) => section.items.map((item) => item.to));
}
