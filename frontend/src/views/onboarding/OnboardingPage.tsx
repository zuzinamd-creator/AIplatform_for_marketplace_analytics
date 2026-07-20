import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../../state/http";
import {
  isOnboardingDone,
  loadWorkspaceProfile,
  saveWorkspaceProfile,
  setOnboardingDone,
  type WorkspaceProfile,
} from "../../state/onboarding";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { Input, Label, Select } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";
import { toast } from "../../ui/toast";

export type StepId =
  | "value-intro"
  | "workspace"
  | "marketplace"
  | "upload"
  | "cost_import"
  | "complete";

export const ONBOARDING_STEPS: Array<{ id: StepId; title: string; why: string; optional?: boolean }> = [
  {
    id: "value-intro",
    title: "Добро пожаловать",
    why: "Короткая настройка, чтобы финансовая аналитика стала полезной как можно быстрее.",
  },
  {
    id: "workspace",
    title: "Профиль рабочего пространства",
    why: "Название помогает отделять демо и реальные магазины (локально, без влияния на данные).",
    optional: true,
  },
  {
    id: "marketplace",
    title: "Выбор маркетплейса",
    why: "Подсказки по отчётам и KPI зависят от выбранного маркетплейса.",
  },
  {
    id: "upload",
    title: "Первая загрузка отчёта",
    why: "Отчёты формируют леджер, агрегаты и основу для аналитики. Нет отчётов — нет KPI.",
  },
  {
    id: "cost_import",
    title: "Загрузка себестоимости",
    why: "Себестоимость нужна для валовой прибыли и маржинальности. Без неё KPI неполные.",
    optional: true,
  },
  {
    id: "complete",
    title: "Готово",
    why: "Базовая настройка завершена — переходите к панели аналитики.",
  },
];

function StepHeader(props: { idx: number; total: number; title: string; why: string }) {
  return (
    <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
      <div>
        <div className="text-2xl font-semibold">{props.title}</div>
        <div className="mt-1 text-sm text-ink-secondary">{props.why}</div>
      </div>
      <StatusBadge tone="info">
        Шаг {props.idx + 1} / {props.total}
      </StatusBadge>
    </div>
  );
}

export function OnboardingPage() {
  const nav = useNavigate();
  const [stepIdx, setStepIdx] = useState(() =>
    isOnboardingDone() ? ONBOARDING_STEPS.length - 1 : 0,
  );
  const step = ONBOARDING_STEPS[stepIdx]!;
  const [marketplaceError, setMarketplaceError] = useState<string | null>(null);

  const [profile, setProfile] = useState<WorkspaceProfile>(() => loadWorkspaceProfile());

  const reports = useQuery({
    queryKey: ["reports", "list", 0, 1],
    queryFn: () => api.reports.list(0, 1),
  });
  const costs = useQuery({
    queryKey: ["costs", "list"],
    queryFn: () => api.costs.list(),
  });

  const hasUpload = (reports.data?.length ?? 0) > 0;
  const hasCosts = (costs.data?.length ?? 0) > 0;

  const suggestedNext = useMemo(() => {
    if (!hasUpload) return "Загрузите первый отчёт, чтобы запустить обработку и KPI.";
    if (!hasCosts) return "При необходимости загрузите себестоимость для точной прибыли.";
    return "Готово — можно переходить к панели аналитики.";
  }, [hasUpload, hasCosts]);

  const next = () => setStepIdx((i) => Math.min(i + 1, ONBOARDING_STEPS.length - 1));
  const back = () => setStepIdx((i) => Math.max(i - 1, 0));

  const tryAdvanceFromMarketplace = () => {
    if (profile.marketplace === "unknown") {
      setMarketplaceError("Выберите маркетплейс, чтобы продолжить настройку.");
      return;
    }
    setMarketplaceError(null);
    saveWorkspaceProfile(profile);
    next();
  };

  const handleNext = () => {
    if (step.id === "marketplace") {
      tryAdvanceFromMarketplace();
      return;
    }
    next();
  };

  const finish = () => {
    setOnboardingDone(true);
    toast("Настройка завершена", "Можно переходить к панели аналитики.");
    nav("/app/analytics");
  };

  return (
    <div className="space-y-6" data-testid="onboarding-page">
      <Card className="p-5">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-semibold">Прогресс настройки</div>
            <div className="mt-1 text-xs text-ink-secondary">{suggestedNext}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={hasUpload ? "ok" : "warn"}>Отчёты</StatusBadge>
            <StatusBadge tone={hasCosts ? "ok" : "warn"}>Себестоимость</StatusBadge>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <StepHeader
          key={step.id}
          idx={stepIdx}
          total={ONBOARDING_STEPS.length}
          title={step.title}
          why={step.why}
        />

        <div className="mt-6" data-testid={`onboarding-step-${step.id}`}>
          {step.id === "value-intro" ? (
            <div className="space-y-3 text-sm text-ink-secondary">
              <div>
                Эта настройка сделана с <span className="font-medium">минимальной когнитивной нагрузкой</span>: только
                шаги, которые реально повышают пользу финансовой панели.
              </div>
              <div className="rounded-lg border border-surface-subtle bg-surface-inset p-3 text-xs text-ink-secondary">
                Подсказка: если где-то “пусто”, чаще всего система ждёт первую загрузку или завершение пересборки.
              </div>
            </div>
          ) : null}

          {step.id === "workspace" ? (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label>Название рабочего пространства</Label>
                <Input
                  value={profile.workspace_name}
                  onChange={(e) => setProfile((p) => ({ ...p, workspace_name: e.target.value }))}
                  placeholder="Например: WB · Магазин"
                />
                <div className="text-xs text-ink-muted">
                  Хранится локально. При необходимости можно добавить серверные настройки позже, не меняя ETL/леджер.
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    saveWorkspaceProfile(profile);
                    toast("Сохранено", "Профиль сохранён локально.");
                  }}
                >
                  Сохранить
                </Button>
                <Button variant="ghost" onClick={next} data-testid="onboarding-skip-workspace">
                  Пропустить
                </Button>
              </div>
            </div>
          ) : null}

          {step.id === "marketplace" ? (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label>Основной маркетплейс</Label>
                <Select
                  value={profile.marketplace}
                  onChange={(e) => {
                    setProfile((p) => ({ ...p, marketplace: e.target.value as WorkspaceProfile["marketplace"] }));
                    setMarketplaceError(null);
                  }}
                >
                  <option value="unknown">Пока не знаю</option>
                  <option value="wildberries">Wildberries</option>
                  <option value="ozon">Ozon</option>
                </Select>
                {marketplaceError ? (
                  <div className="text-xs text-semantic-danger" data-testid="onboarding-marketplace-error">
                    {marketplaceError}
                  </div>
                ) : null}
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  if (profile.marketplace === "unknown") {
                    setMarketplaceError("Выберите маркетплейс, чтобы сохранить настройку.");
                    return;
                  }
                  saveWorkspaceProfile(profile);
                  toast("Сохранено", "Выбор маркетплейса сохранён локально.");
                }}
              >
                Сохранить
              </Button>
            </div>
          ) : null}

          {step.id === "upload" ? (
            <div className="space-y-4 text-sm">
              <div className="text-ink-secondary">
                Загрузите первый отчёт. Прогресс обработки виден в разделе «Отчёты».
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  to="/app/reports/upload"
                  className="rounded-lg bg-sky-500/90 px-4 py-2 text-sm font-medium text-white hover:bg-sky-400"
                >
                  Перейти к загрузке
                </Link>
                <Link to="/app/reports" className="btn-secondary">
                  История отчётов
                </Link>
              </div>
              {hasUpload ? (
                <div className="text-xs text-emerald-200">Обнаружено: уже есть хотя бы один загруженный отчёт.</div>
              ) : (
                <div className="text-xs text-ink-muted">Пока нет загруженных отчётов.</div>
              )}
            </div>
          ) : null}

          {step.id === "cost_import" ? (
            <div className="space-y-4 text-sm">
              <div className="text-ink-secondary">
                Загрузите себестоимость, чтобы валовая прибыль и маржинальность стали финансово корректными.
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  to="/app/costs"
                  className="rounded-lg bg-sky-500/90 px-4 py-2 text-sm font-medium text-white hover:bg-sky-400"
                >
                  Перейти к себестоимости
                </Link>
                <Button variant="ghost" onClick={next} data-testid="onboarding-skip-costs">
                  Пропустить
                </Button>
              </div>
              {hasCosts ? (
                <div className="text-xs text-emerald-200">Обнаружено: себестоимость уже загружена.</div>
              ) : (
                <div className="text-xs text-ink-muted">Пока нет данных себестоимости.</div>
              )}
            </div>
          ) : null}

          {step.id === "complete" ? (
            <div className="space-y-4 text-sm text-ink-secondary">
              <div>
                Базовая настройка завершена. На панели аналитики вы увидите выручку, приоритетные действия и топ SKU за
                выбранный период.
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={finish} data-testid="onboarding-open-dashboard">
                  Открыть панель
                </Button>
                <Link to="/app/ai/recommendations" className="btn-secondary">
                  ИИ-помощник
                </Link>
              </div>
            </div>
          ) : null}
        </div>

        <div className="mt-6 flex items-center justify-between gap-2">
          <Button variant="ghost" onClick={back} disabled={stepIdx === 0}>
            Назад
          </Button>
          <div className="flex gap-2">
            <Link to="/app/analytics" className="btn-secondary h-9">
              Пропустить и перейти к панели
            </Link>
            {step.id !== "complete" ? (
              <Button variant="secondary" onClick={handleNext} data-testid="onboarding-next">
                Далее
              </Button>
            ) : null}
          </div>
        </div>
      </Card>
    </div>
  );
}
