import { Link } from "react-router-dom";
import { CheckSquare, Upload, Wallet, LineChart, Bot, X } from "lucide-react";
import { useState } from "react";

import { Card } from "./card";
import { Button } from "./button";
import { dismissFirstRunChecklist, isFirstRunChecklistDismissed } from "../state/first-run";

export function FirstRunChecklist() {
  const [hidden, setHidden] = useState(() => isFirstRunChecklistDismissed());
  if (hidden) return null;

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <CheckSquare className="h-4 w-4 text-brand" />
            Первый запуск: чек‑лист продавца
          </div>
          <div className="mt-1 text-xs text-ink-muted">Помогает настроить систему под ежедневную работу на локальной машине.</div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Скрыть чек-лист"
          onClick={() => {
            dismissFirstRunChecklist();
            setHidden(true);
          }}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="mt-3 grid gap-2 md:grid-cols-2">
        <Link to="/app/reports/upload" className="rounded-xl border border-surface-subtle bg-surface-inset p-4 transition hover:border-brand-muted hover:bg-brand-subtle">
          <div className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <Upload className="h-4 w-4 text-brand" /> 1) Загрузить отчёт WB/Ozon
          </div>
          <div className="mt-1 text-xs text-ink-muted">Нужен хотя бы один период, чтобы увидеть KPI и тренды.</div>
        </Link>
        <Link to="/app/costs" className="rounded-xl border border-surface-subtle bg-surface-inset p-4 transition hover:border-brand-muted hover:bg-brand-subtle">
          <div className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <Wallet className="h-4 w-4 text-brand" /> 2) Импортировать себестоимость
          </div>
          <div className="mt-1 text-xs text-ink-muted">Без себестоимости прибыль и маржа будут менее точными.</div>
        </Link>
        <Link to="/app/economics" className="rounded-xl border border-surface-subtle bg-surface-inset p-4 transition hover:border-brand-muted hover:bg-brand-subtle">
          <div className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <LineChart className="h-4 w-4 text-brand" /> 3) Открыть «Экономика SKU»
          </div>
          <div className="mt-1 text-xs text-ink-muted">Посмотреть прибыльность и драйверы затрат.</div>
        </Link>
        <Link to="/app/dashboard" className="rounded-xl border border-surface-subtle bg-surface-inset p-4 transition hover:border-brand-muted hover:bg-brand-subtle">
          <div className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <Bot className="h-4 w-4 text-brand" /> 4) Запустить ИИ‑анализ периода
          </div>
          <div className="mt-1 text-xs text-ink-muted">ИИ advisory: показывает ограничения и снижает уверенность при плохих данных.</div>
        </Link>
      </div>
    </Card>
  );
}

