import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bot,
  Database,
  Gauge,
  LayoutDashboard,
  LifeBuoy,
  LineChart,
  Mail,
  Package,
  Server,
  Settings,
  Settings2,
  Shield,
  Upload,
  Users,
} from "lucide-react";

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

const dashboardItems: NavItem[] = [
  { to: "/app/dashboard", label: "Панель", icon: LayoutDashboard },
  { to: "/app/today", label: "Сегодня", icon: Gauge },
];

const analyticsItems: NavItem[] = [
  { to: "/app/economics", label: "Экономика SKU", icon: LineChart },
  { to: "/app/economics/inventory", label: "Склад и оборот", icon: Package },
  { to: "/app/finance/reconciliation", label: "Сверка выплат", icon: Shield },
];

const reportsItems: NavItem[] = [
  { to: "/app/reports", label: "Отчёты", icon: Database },
  { to: "/app/reports/upload", label: "Загрузка", icon: Upload },
  { to: "/app/costs", label: "Себестоимость", icon: Database },
];

const aiItems: NavItem[] = [
  { to: "/app/ai/recommendations", label: "ИИ-помощник", icon: Bot },
  { to: "/app/ai/today", label: "Фокус на сегодня", icon: Bot },
  { to: "/app/ai/digest", label: "Дайджест ИИ", icon: Bot },
  { to: "/app/ai/usage", label: "Расход ИИ", icon: Bot },
  { to: "/app/ai/runs", label: "История ИИ", icon: Bot },
];

const administrationItems: NavItem[] = [
  { to: "/app/admin/users", label: "Пользователи", icon: Users },
  { to: "/app/admin/invites", label: "Приглашения", icon: Mail },
];

const adminItems: NavItem[] = [
  { to: "/app/onboarding", label: "Настройка", icon: Settings2 },
  { to: "/app/settings", label: "Настройки", icon: Settings },
  { to: "/app/support", label: "Поддержка", icon: LifeBuoy },
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

const sellerSections: NavSection[] = [
  { id: "dashboard", label: "Dashboard", items: dashboardItems },
  { id: "analytics", label: "Analytics", items: analyticsItems },
  { id: "reports", label: "Reports", items: reportsItems },
  { id: "ai", label: "AI", items: aiItems },
];

const adminSections: NavSection[] = [
  { id: "administration", label: "Администрирование", items: administrationItems },
  { id: "admin", label: "Admin", items: adminItems },
  { id: "operations", label: "Operations", items: operationsItems },
  { id: "system", label: "System", items: systemItems },
];

export function buildNavSections(user: UserResponse | null | undefined): NavSection[] {
  if (isPlatformAdmin(user)) {
    return [...sellerSections, ...adminSections];
  }
  return sellerSections;
}
