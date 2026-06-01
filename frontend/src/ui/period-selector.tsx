import { useEffect, useMemo, useState } from "react";

import { Card } from "./card";
import { Label, Input, Select } from "./field";
import { loadPeriodSelection, savePeriodSelection, computePreset, previousPeriod, type PeriodSelection, type PeriodPreset } from "../state/period";

const presetOptions: Array<{ value: PeriodPreset; label: string }> = [
  { value: "today", label: "Сегодня" },
  { value: "yesterday", label: "Вчера" },
  { value: "7d", label: "Последние 7 дней" },
  { value: "14d", label: "Последние 14 дней" },
  { value: "30d", label: "Последние 30 дней" },
  { value: "current_month", label: "Текущий месяц" },
  { value: "previous_month", label: "Прошлый месяц" },
  { value: "custom", label: "Произвольный период" },
];

export function PeriodSelector(props: { onChange?: (sel: PeriodSelection) => void }) {
  const [sel, setSel] = useState<PeriodSelection>(() => loadPeriodSelection());

  useEffect(() => {
    savePeriodSelection(sel);
    props.onChange?.(sel);
  }, [sel]);

  const compareRange = useMemo(() => {
    if (!sel.compareEnabled) return null;
    if (sel.comparePreset === "custom") return sel.compareRange ?? previousPeriod(sel.range);
    return previousPeriod(sel.range);
  }, [sel]);

  return (
    <Card className="p-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-12 md:items-end">
        <div className="md:col-span-4">
          <Label>Период</Label>
          <Select
            value={sel.preset}
            onChange={(e) => {
              const preset = e.target.value as PeriodPreset;
              const range = preset === "custom" ? sel.range : computePreset(preset);
              setSel((s) => ({ ...s, preset, range }));
            }}
          >
            {presetOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>

        <div className="md:col-span-3">
          <Label>С</Label>
          <Input
            type="date"
            value={sel.range.start}
            onChange={(e) => setSel((s) => ({ ...s, preset: "custom", range: { ...s.range, start: e.target.value } }))}
          />
        </div>
        <div className="md:col-span-3">
          <Label>По</Label>
          <Input
            type="date"
            value={sel.range.end}
            onChange={(e) => setSel((s) => ({ ...s, preset: "custom", range: { ...s.range, end: e.target.value } }))}
          />
        </div>

        <div className="md:col-span-2">
          <Label>Сравнение</Label>
          <Select
            value={sel.compareEnabled ? sel.comparePreset : "off"}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "off") {
                setSel((s) => ({ ...s, compareEnabled: false }));
                return;
              }
              if (v === "custom") {
                const base = sel.compareRange ?? previousPeriod(sel.range);
                setSel((s) => ({ ...s, compareEnabled: true, comparePreset: "custom", compareRange: base }));
                return;
              }
              setSel((s) => ({ ...s, compareEnabled: true, comparePreset: "previous_period" }));
            }}
          >
            <option value="off">Выключено</option>
            <option value="previous_period">Предыдущий период</option>
            <option value="custom">Период B (вручную)</option>
          </Select>
        </div>

        {sel.compareEnabled && sel.comparePreset === "custom" ? (
          <div className="md:col-span-12 grid grid-cols-1 gap-3 md:grid-cols-6">
            <div className="md:col-span-3">
              <Label>Период B: с</Label>
              <Input
                type="date"
                value={(sel.compareRange ?? compareRange)?.start ?? ""}
                onChange={(e) =>
                  setSel((s) => ({
                    ...s,
                    compareEnabled: true,
                    comparePreset: "custom",
                    compareRange: { start: e.target.value, end: s.compareRange?.end ?? e.target.value },
                  }))
                }
              />
            </div>
            <div className="md:col-span-3">
              <Label>Период B: по</Label>
              <Input
                type="date"
                value={(sel.compareRange ?? compareRange)?.end ?? ""}
                onChange={(e) =>
                  setSel((s) => ({
                    ...s,
                    compareEnabled: true,
                    comparePreset: "custom",
                    compareRange: { start: s.compareRange?.start ?? e.target.value, end: e.target.value },
                  }))
                }
              />
            </div>
          </div>
        ) : null}

        <div className="md:col-span-12 text-xs text-slate-400">
          Данные проанализированы за период: <span className="text-slate-200">{sel.range.start} → {sel.range.end}</span>
          {compareRange ? (
            <>
              {" "}· Сравнение: <span className="text-slate-200">{compareRange.start} → {compareRange.end}</span>
            </>
          ) : null}
        </div>
      </div>
    </Card>
  );
}

