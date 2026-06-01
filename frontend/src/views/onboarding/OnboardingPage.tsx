import { useMutation, useQuery } from "@tanstack/react-query";
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

type StepId =
  | "welcome"
  | "workspace"
  | "marketplace"
  | "upload"
  | "sku_mapping"
  | "cost_import"
  | "first_ai"
  | "walkthrough";

const steps: Array<{ id: StepId; title: string; why: string }> = [
  {
    id: "welcome",
    title: "Добро пожаловать",
    why: "Короткая настройка, чтобы финансовая аналитика стала полезной как можно быстрее.",
  },
  {
    id: "workspace",
    title: "Профиль рабочего пространства",
    why: "Название помогает отделять демо и реальные магазины (локально, без влияния на данные).",
  },
  {
    id: "marketplace",
    title: "Выбор маркетплейса",
    why: "Подсказки по отчётам и KPI зависят от выбранного маркетплейса.",
  },
  {
    id: "upload",
    title: "Первая загрузка отчёта",
    why: "Отчёты формируют леджер, агрегаты и основу для ИИ. Нет отчётов — нет аналитики.",
  },
  {
    id: "sku_mapping",
    title: "Сопоставление SKU (подсказки)",
    why: "Сопоставление SKU нужно для устойчивой себестоимости и прибыльности.",
  },
  {
    id: "cost_import",
    title: "Загрузка себестоимости",
    why: "Себестоимость нужна для валовой прибыли и маржинальности. Без неё KPI неполные.",
  },
  {
    id: "first_ai",
    title: "Первый запуск ИИ-анализа",
    why: "Рекомендации ИИ точнее, когда есть свежие данные и понятна свежесть/полнота аналитики.",
  },
  {
    id: "walkthrough",
    title: "Куда смотреть каждый день",
    why: "Покажем ежедневный маршрут: загрузки → статус → KPI → предупреждения → ИИ-действия.",
  },
];

function StepHeader(props: { idx: number; total: number; title: string; why: string }) {
  return (
    <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
      <div>
        <div className="text-2xl font-semibold">{props.title}</div>
        <div className="mt-1 text-sm text-slate-300">{props.why}</div>
      </div>
      <StatusBadge tone="info">
        Шаг {props.idx + 1} / {props.total}
      </StatusBadge>
    </div>
  );
}

export function OnboardingPage() {
  const nav = useNavigate();
  const [stepIdx, setStepIdx] = useState(() => (isOnboardingDone() ? steps.length - 1 : 0));
  const step = steps[stepIdx]!;

  const [profile, setProfile] = useState<WorkspaceProfile>(() => loadWorkspaceProfile());

  const reports = useQuery({
    queryKey: ["reports", "list", 0, 1],
    queryFn: () => api.reports.list(0, 1),
  });
  const costs = useQuery({
    queryKey: ["costs", "list"],
    queryFn: () => api.costs.list(),
  });
  const runs = useQuery({
    queryKey: ["ai", "runs", 0, 1],
    queryFn: () => api.ai.runs(0, 1),
  });

  const hasUpload = (reports.data?.length ?? 0) > 0;
  const hasCosts = (costs.data?.length ?? 0) > 0;
  const hasAiRuns = ((runs.data as any)?.items?.length ?? 0) > 0;

  const suggestedNext = useMemo(() => {
    if (!hasUpload) return "Загрузите первый отчёт, чтобы запустить обработку и KPI.";
    if (!hasCosts) return "Загрузите себестоимость, чтобы включить финансово корректную прибыль и маржу.";
    if (!hasAiRuns) return "Запустите первый ИИ-анализ для рекомендаций.";
    return "Готово — можно переходить к панели аналитики.";
  }, [hasUpload, hasCosts, hasAiRuns]);

  const runFirstAi = useMutation({
    mutationFn: async () => {
      const reportId = reports.data?.[0]?.id ?? null;
      // Uses in-code prompt registry: app/ai/prompts/registry.py
      return await api.ai.runIntelligence({
        workflow: "inventory_insight",
        prompt_id: "inventory.insight.v1",
        semantics_version: "1.0",
        report_id: reportId,
      });
    },
    onSuccess: (res) => {
      toast("ИИ-анализ запущен", res.summary || "Создан запуск.");
    },
    onError: (err) => toast("ИИ-анализ не запустился", err instanceof Error ? err.message : "Неизвестная ошибка"),
  });

  const next = () => setStepIdx((i) => Math.min(i + 1, steps.length - 1));
  const back = () => setStepIdx((i) => Math.max(i - 1, 0));

  const finish = () => {
    setOnboardingDone(true);
    toast("Настройка завершена", "Можно переходить к панели аналитики.");
    nav("/app/dashboard");
  };

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-sm font-semibold">Прогресс настройки</div>
            <div className="mt-1 text-xs text-slate-300">{suggestedNext}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={hasUpload ? "ok" : "warn"}>Отчёты</StatusBadge>
            <StatusBadge tone={hasCosts ? "ok" : "warn"}>Себестоимость</StatusBadge>
            <StatusBadge tone={hasAiRuns ? "ok" : "warn"}>ИИ</StatusBadge>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <StepHeader key={step.id} idx={stepIdx} total={steps.length} title={step.title} why={step.why} />

        <div className="mt-6">
          {step.id === "welcome" ? (
            <div className="space-y-3 text-sm text-slate-200">
              <div>
                Эта настройка сделана с <span className="font-medium">минимальной когнитивной нагрузкой</span>: только шаги,
                которые реально повышают пользу финансовой панели.
              </div>
              <div className="rounded-lg border border-slate-800/70 bg-slate-950/40 p-3 text-xs text-slate-300">
                Подсказка: если где-то “пусто”, чаще всего система ждёт первую загрузку или завершение пересборки.
                Операционные страницы — только для просмотра.
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
                <div className="text-xs text-slate-400">
                  Хранится локально. При необходимости можно добавить серверные настройки позже, не меняя ETL/леджер.
                </div>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  saveWorkspaceProfile(profile);
                  toast("Сохранено", "Профиль сохранён локально.");
                }}
              >
                Сохранить
              </Button>
            </div>
          ) : null}

          {step.id === "marketplace" ? (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label>Основной маркетплейс</Label>
                <Select
                  value={profile.marketplace}
                  onChange={(e) =>
                    setProfile((p) => ({ ...p, marketplace: e.target.value as WorkspaceProfile["marketplace"] }))
                  }
                >
                  <option value="unknown">Пока не знаю</option>
                  <option value="wildberries">Wildberries</option>
                  <option value="ozon">Ozon</option>
                </Select>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
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
              <div className="text-slate-200">
                Загрузите первый отчёт. Прогресс обработки виден в “Отчёты” и “Очередь”.
              </div>
              <div className="flex flex-wrap gap-2">
                <Link to="/app/reports/upload" className="rounded-lg bg-sky-500/90 px-4 py-2 text-sm font-medium text-white hover:bg-sky-400">
                  Перейти к загрузке
                </Link>
                <Link to="/app/reports" className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 hover:bg-slate-700">
                  История отчётов
                </Link>
              </div>
              {hasUpload ? (
                <div className="text-xs text-emerald-200">Обнаружено: уже есть хотя бы один загруженный отчёт.</div>
              ) : (
                <div className="text-xs text-slate-400">Пока нет загруженных отчётов.</div>
              )}
            </div>
          ) : null}

          {step.id === "sku_mapping" ? (
            <div className="space-y-3 text-sm text-slate-200">
              <div>
                Сопоставление SKU — реальная потребность продавца, но сейчас нет API для управления сопоставлениями.
              </div>
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
                Подсказка: позже можно добавить API сопоставлений как tenant-scoped проекцию (без редизайна ETL/леджера).
              </div>
              <div className="text-xs text-slate-400">
                Рекомендуемый подход:
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  <li>Определите внутренние SKU (ваш мастер-каталог).</li>
                  <li>Сопоставьте SKU маркетплейса → внутренний SKU.</li>
                  <li>Используйте внутренний SKU для себестоимости и прибыльности.</li>
                </ul>
              </div>
            </div>
          ) : null}

          {step.id === "cost_import" ? (
            <div className="space-y-4 text-sm">
              <div className="text-slate-200">
                Загрузите себестоимость, чтобы валовая прибыль и маржинальность стали финансово корректными.
              </div>
              <div className="flex flex-wrap gap-2">
                <Link to="/app/costs" className="rounded-lg bg-sky-500/90 px-4 py-2 text-sm font-medium text-white hover:bg-sky-400">
                  Перейти к себестоимости
                </Link>
              </div>
              {hasCosts ? (
                <div className="text-xs text-emerald-200">Обнаружено: себестоимость уже загружена.</div>
              ) : (
                <div className="text-xs text-slate-400">Пока нет данных себестоимости.</div>
              )}
            </div>
          ) : null}

          {step.id === "first_ai" ? (
            <div className="space-y-4 text-sm">
              <div className="text-slate-200">
                Запустите первый ИИ-анализ (инвентарь). Он создаст запуск и может сформировать рекомендацию.
              </div>
              <div className="rounded-lg border border-slate-800/70 bg-slate-950/40 p-3 text-xs text-slate-300">
                Используется prompt id <span className="font-mono">inventory.insight.v1</span> и workflow{" "}
                <span className="font-mono">inventory_insight</span>.
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  disabled={runFirstAi.isPending}
                  onClick={() => runFirstAi.mutate()}
                >
                  {runFirstAi.isPending ? "Запуск…" : "Запустить ИИ-анализ"}
                </Button>
                <Link to="/app/ai/recommendations" className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 hover:bg-slate-700">
                  Открыть рекомендации
                </Link>
                <Link to="/app/ai/runs" className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 hover:bg-slate-700">
                  История запусков
                </Link>
              </div>
              {hasAiRuns ? (
                <div className="text-xs text-emerald-200">Обнаружено: уже есть хотя бы один запуск ИИ.</div>
              ) : null}
            </div>
          ) : null}

          {step.id === "walkthrough" ? (
            <div className="space-y-4 text-sm text-slate-200">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <Card className="p-4">
                  <div className="text-sm font-semibold">Ежедневный ритм</div>
                  <div className="mt-2 text-xs text-slate-300">
                    Загрузка → статус обработки → KPI/предупреждения → рекомендации ИИ.
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm font-semibold">Если что-то выглядит странно</div>
                  <div className="mt-2 text-xs text-slate-300">
                    Проверьте очередь/пересборки/дрейф, затем детали аномалий и объяснимость ИИ.
                  </div>
                </Card>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button onClick={finish}>Завершить</Button>
                <Link to="/app/dashboard" className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 hover:bg-slate-700">
                  Перейти к панели
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
            <Link to="/app/dashboard" className="rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-slate-800/60">
              Пропустить и перейти к панели
            </Link>
            <Button variant="secondary" onClick={next} disabled={stepIdx === steps.length - 1}>
              Далее
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

