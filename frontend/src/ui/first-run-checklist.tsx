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
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <CheckSquare className="h-4 w-4 text-sky-200" />
            Первый запуск: чек‑лист продавца
          </div>
          <div className="mt-1 text-xs text-slate-400">Помогает настроить систему под ежедневную работу на локальной машине.</div>
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
        <Link to="/app/reports/upload" className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:bg-slate-900/30">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <Upload className="h-4 w-4" /> 1) Загрузить отчёт WB/Ozon
          </div>
          <div className="mt-1 text-xs text-slate-400">Нужен хотя бы один период, чтобы увидеть KPI и тренды.</div>
        </Link>
        <Link to="/app/costs" className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:bg-slate-900/30">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <Wallet className="h-4 w-4" /> 2) Импортировать себестоимость
          </div>
          <div className="mt-1 text-xs text-slate-400">Без себестоимости прибыль и маржа будут менее точными.</div>
        </Link>
        <Link to="/app/economics" className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:bg-slate-900/30">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <LineChart className="h-4 w-4" /> 3) Открыть “Экономика SKU”
          </div>
          <div className="mt-1 text-xs text-slate-400">Посмотреть прибыльность и драйверы затрат.</div>
        </Link>
        <Link to="/app/dashboard" className="rounded-lg border border-slate-800 bg-slate-950/40 p-3 hover:bg-slate-900/30">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <Bot className="h-4 w-4" /> 4) Запустить ИИ‑анализ периода
          </div>
          <div className="mt-1 text-xs text-slate-400">ИИ advisory: показывает ограничения и снижает уверенность при плохих данных.</div>
        </Link>
      </div>
    </Card>
  );
}

