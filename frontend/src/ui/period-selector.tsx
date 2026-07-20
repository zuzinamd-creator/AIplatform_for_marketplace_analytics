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

export function PeriodSelector(props: {
  value?: PeriodSelection;
  onChange?: (sel: PeriodSelection) => void;
}) {
  const [internalSel, setInternalSel] = useState<PeriodSelection>(() => loadPeriodSelection());
  const controlled = props.value !== undefined && props.onChange !== undefined;
  const sel = controlled ? props.value! : internalSel;

  const updateSel = (next: PeriodSelection | ((prev: PeriodSelection) => PeriodSelection)) => {
    if (controlled) {
      const resolved = typeof next === "function" ? next(props.value!) : next;
      props.onChange!(resolved);
      return;
    }
    setInternalSel(next);
  };

  useEffect(() => {
    if (!controlled) {
      savePeriodSelection(internalSel);
      props.onChange?.(internalSel);
    }
  }, [controlled, internalSel]);

  useEffect(() => {
    if (controlled) {
      savePeriodSelection(props.value!);
    }
  }, [controlled, props.value]);

  const compareRange = useMemo(() => {
    if (!sel.compareEnabled) return null;
    if (sel.comparePreset === "custom") return sel.compareRange ?? previousPeriod(sel.range);
    return previousPeriod(sel.range);
  }, [sel]);

  return (
    <Card className="p-5" data-testid="period-selector">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-12 md:items-end">
        <div className="md:col-span-4">
          <Label>Период</Label>
          <Select
            value={sel.preset}
            onChange={(e) => {
              const preset = e.target.value as PeriodPreset;
              const range = preset === "custom" ? sel.range : computePreset(preset);
              updateSel((s) => ({ ...s, preset, range }));
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
            onChange={(e) => updateSel((s) => ({ ...s, preset: "custom", range: { ...s.range, start: e.target.value } }))}
          />
        </div>
        <div className="md:col-span-3">
          <Label>По</Label>
          <Input
            type="date"
            value={sel.range.end}
            onChange={(e) => updateSel((s) => ({ ...s, preset: "custom", range: { ...s.range, end: e.target.value } }))}
          />
        </div>

        <div className="md:col-span-2">
          <Label>Сравнение</Label>
          <Select
            value={sel.compareEnabled ? sel.comparePreset : "off"}
            onChange={(e) => {
              const v = e.target.value;
              if (v === "off") {
                updateSel((s) => ({ ...s, compareEnabled: false }));
                return;
              }
              if (v === "custom") {
                const base = sel.compareRange ?? previousPeriod(sel.range);
                updateSel((s) => ({ ...s, compareEnabled: true, comparePreset: "custom", compareRange: base }));
                return;
              }
              updateSel((s) => ({ ...s, compareEnabled: true, comparePreset: "previous_period" }));
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
                  updateSel((s) => ({
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
                  updateSel((s) => ({
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

        <div className="md:col-span-12 text-xs text-ink-muted">
          Данные проанализированы за период: <span className="font-medium text-ink-secondary">{sel.range.start} → {sel.range.end}</span>
          {compareRange ? (
            <>
              {" "}· Сравнение: <span className="font-medium text-ink-secondary">{compareRange.start} → {compareRange.end}</span>
            </>
          ) : null}
        </div>
      </div>
    </Card>
  );
}

