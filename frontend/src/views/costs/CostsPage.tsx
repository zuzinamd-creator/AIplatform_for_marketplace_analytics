import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";

import { api, formatApiError } from "../../state/http";
import type { CostResponse } from "../../state/types-costs";
import { formatMetric } from "../../utils/format";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { Input, Label, Select } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";
import { toast } from "../../ui/toast";

type EditableField = "product_cost" | "packaging_cost" | "inbound_logistics_cost" | "additional_cost";

type ViewMode = "all" | "as_of";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function fmtDate(iso: string): string {
  const d = iso.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return iso;
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y}`;
}

/** Read-only cell display — editing still uses raw API strings. */
function displayCost(v: unknown): string {
  if (v == null || v === "") return "—";
  return formatMetric(v);
}

function numOrEmpty(v: string): string {
  const t = v.trim().replace(",", ".");
  if (!t) return "";
  const n = Number(t);
  return Number.isFinite(n) ? String(n) : v;
}

export function CostsPage() {
  const qc = useQueryClient();
  const [picked, setPicked] = useState<File | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("all");
  const [viewDate, setViewDate] = useState(todayIso);
  const [skuFilter, setSkuFilter] = useState("");
  const [editing, setEditing] = useState<{ id: string; field: EditableField } | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});

  const listParams = useMemo(() => {
    const sku = skuFilter.trim() || undefined;
    if (viewMode === "as_of") {
      return { sku, as_of: viewDate };
    }
    return { sku };
  }, [skuFilter, viewMode, viewDate]);

  const list = useQuery({
    queryKey: ["costs", "list", listParams],
    queryFn: () => api.costs.list(listParams),
  });

  const preview = useQuery({
    queryKey: ["costs", "importPreview", picked?.name ?? "", picked?.size ?? 0],
    queryFn: async () => {
      if (!picked) return null;
      return await api.costs.previewImport(picked);
    },
    enabled: Boolean(picked) && showPreview,
  });

  const imp = useMutation({
    mutationFn: async () => {
      if (!picked) throw new Error("Сначала выберите файл.");
      return await api.costs.importV2(picked);
    },
    onSuccess: async (res) => {
      toast(
        "Импорт завершён",
        `SKU: ${res.imported_distinct_skus} · строк импортировано: ${res.imported_rows} · пропущено: ${res.skipped_rows}`,
      );
      setPicked(null);
      await qc.invalidateQueries({ queryKey: ["costs", "list"] });
      await qc.invalidateQueries({ queryKey: ["analytics", "coverage"] });
      await qc.invalidateQueries({ queryKey: ["analytics", "costCoverage"] });
      await qc.invalidateQueries({ queryKey: ["ai", "recommendations"] });
    },
    onError: (err) => toast("Ошибка импорта", formatApiError(err)),
  });

  const saveCell = useMutation({
    mutationFn: async ({
      row,
      field,
      value,
    }: {
      row: CostResponse;
      field: EditableField;
      value: string;
    }) => {
      const normalized = numOrEmpty(value);
      if (!normalized) throw new Error("Значение не может быть пустым.");
      return await api.costs.update(row.id, { [field]: normalized });
    },
    onSuccess: async () => {
      setEditing(null);
      setDraft({});
      await qc.invalidateQueries({ queryKey: ["costs", "list"] });
      toast("Сохранено", "Себестоимость обновлена.");
    },
    onError: (err) => toast("Ошибка сохранения", formatApiError(err)),
  });

  const downloadTemplate = useMutation({
    mutationFn: () => api.costs.downloadImportTemplate(),
    onError: (err) => toast("Не удалось скачать", formatApiError(err)),
  });

  const dz = useDropzone({
    multiple: false,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
    },
    onDrop: (files) => setPicked(files[0] ?? null),
  });

  const hint = useMemo(() => {
    if (!picked) return "Перетащите CSV или Excel сюда (или нажмите для выбора).";
    return `${picked.name} • ${(picked.size / 1024 / 1024).toFixed(2)} MB`;
  }, [picked]);

  const startEdit = (row: CostResponse, field: EditableField) => {
    setEditing({ id: row.id, field });
    setDraft((d) => ({ ...d, [`${row.id}:${field}`]: String(row[field] ?? "") }));
  };

  const commitEdit = (row: CostResponse, field: EditableField) => {
    const key = `${row.id}:${field}`;
    const value = draft[key] ?? String(row[field] ?? "");
    saveCell.mutate({ row, field, value });
  };

  const renderEditable = (row: CostResponse, field: EditableField) => {
    const key = `${row.id}:${field}`;
    const isActive = editing?.id === row.id && editing.field === field;
    if (isActive) {
      return (
        <Input
          className="h-8 w-24 text-xs"
          value={draft[key] ?? ""}
          autoFocus
          onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}
          onBlur={() => commitEdit(row, field)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitEdit(row, field);
            if (e.key === "Escape") {
              setEditing(null);
              setDraft({});
            }
          }}
        />
      );
    }
    return (
      <button
        type="button"
        className="rounded px-1 text-left hover:bg-surface-inset"
        onClick={() => startEdit(row, field)}
        title="Нажмите для редактирования"
      >
        {displayCost(row[field])}
      </button>
    );
  };

  return (
    <div className="page-shell">
      <div>
        <h1 className="page-title">Себестоимость</h1>
        <p className="page-subtitle">
          Импорт по SKU и ручное редактирование ячеек. Данные привязаны к вашему аккаунту.
        </p>
      </div>

      <CollapsibleSection
        title="Импорт файла"
        subtitle="CSV или Excel — перетащите или выберите файл"
        defaultOpen
      >
        <div
          {...dz.getRootProps()}
          className="cursor-pointer rounded-xl border border-dashed border-surface-subtle bg-surface-inset p-8 text-center"
          role="button"
          tabIndex={0}
          aria-label="Зона импорта себестоимости"
        >
          <input {...dz.getInputProps()} />
          <div className="text-sm font-medium">{hint}</div>
          <div className="mt-1 text-xs text-ink-muted">
            Совет: используйте шаблон и заполняйте себестоимость в одной валюте.
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            disabled={downloadTemplate.isPending}
            onClick={() => downloadTemplate.mutate()}
          >
            {downloadTemplate.isPending ? "Скачивание…" : "Скачать шаблон"}
          </Button>
          <Button disabled={!picked || imp.isPending} onClick={() => imp.mutate()}>
            {imp.isPending ? "Импорт…" : "Импортировать"}
          </Button>
          <Button variant="ghost" disabled={imp.isPending} onClick={() => setPicked(null)}>
            Сбросить файл
          </Button>
        </div>

        {picked && preview.data ? (
          <div className="mt-4 rounded-lg border border-surface-subtle bg-surface-inset p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">Проверка файла перед импортом</div>
                <div className="mt-1 text-xs text-ink-muted">
                  Строк в файле: {preview.data.total_rows}. Показаны первые {preview.data.preview_rows.length}.
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowPreview((v) => !v)}>
                {showPreview ? "Скрыть превью" : "Показать превью"}
              </Button>
            </div>

            {(preview.data.issues ?? []).length ? (
              <div className="mt-3 space-y-1 text-xs text-ink-secondary">
                {preview.data.issues.slice(0, 8).map((it, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <StatusBadge tone={it.severity === "error" ? "bad" : "warn"}>{it.code}</StatusBadge>
                    <div>
                      {it.message}
                      {it.row_index != null ? <span className="text-ink-muted"> (строка {it.row_index})</span> : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 text-xs text-ink-muted">Ошибок структуры не найдено. Можно импортировать.</div>
            )}

            {showPreview ? (
              <div className="mt-3 overflow-auto rounded-lg border border-surface-subtle">
                <table className="table-shell min-w-[880px] w-full text-xs">
                  <thead>
                    <tr>
                      <th className="px-3 py-2">#</th>
                      <th className="px-3 py-2">SKU</th>
                      <th className="px-3 py-2">Дата</th>
                      <th className="px-3 py-2">Себестоимость</th>
                      <th className="px-3 py-2">Упаковка</th>
                      <th className="px-3 py-2">Логистика</th>
                      <th className="px-3 py-2">Доп.</th>
                      <th className="px-3 py-2">Итого</th>
                      <th className="px-3 py-2">Валюта</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.data.preview_rows.map((r) => (
                      <tr key={r.row_index}>
                        <td className="px-3 py-2 text-ink-muted">{r.row_index}</td>
                        <td className="px-3 py-2">{r.internal_sku ?? "—"}</td>
                        <td className="px-3 py-2">{r.effective_from ?? "—"}</td>
                        <td className="px-3 py-2">{displayCost(r.product_cost)}</td>
                        <td className="px-3 py-2">{displayCost(r.packaging_cost)}</td>
                        <td className="px-3 py-2">{displayCost(r.inbound_logistics_cost)}</td>
                        <td className="px-3 py-2">{displayCost(r.additional_cost)}</td>
                        <td className="px-3 py-2">{displayCost(r.total_cost)}</td>
                        <td className="px-3 py-2">{r.currency ?? "RUB"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : picked && preview.isLoading ? (
          <div className="mt-4 text-xs text-ink-muted">Проверяем файл…</div>
        ) : picked && preview.isError ? (
          <div className="mt-4 text-xs text-semantic-danger">Не удалось проверить файл: {formatApiError(preview.error)}</div>
        ) : null}
      </CollapsibleSection>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-surface-subtle bg-surface-inset px-4 py-4">
          <div>
            <div className="text-sm font-semibold text-ink">Загруженная себестоимость</div>
            <div className="mt-1 text-xs text-ink-muted">Клик по ячейке суммы — редактирование без повторного импорта.</div>
          </div>
          <StatusBadge tone="info">{list.isLoading ? "…" : `${list.data?.length ?? 0} строк`}</StatusBadge>
        </div>

        <div className="flex flex-wrap items-end gap-3 border-b border-surface-subtle px-4 py-4">
          <div className="space-y-1.5">
            <Label>Режим просмотра</Label>
            <Select value={viewMode} onChange={(e) => setViewMode(e.target.value as ViewMode)}>
              <option value="all">Вся история</option>
              <option value="as_of">На дату</option>
            </Select>
          </div>
          {viewMode === "as_of" ? (
            <div className="space-y-1.5">
              <Label>Дата</Label>
              <Input type="date" className="h-9 w-40" value={viewDate} onChange={(e) => setViewDate(e.target.value)} />
            </div>
          ) : null}
          <div className="space-y-1.5">
            <Label>Фильтр SKU</Label>
            <Input
              className="h-9 w-48"
              placeholder="необязательно"
              value={skuFilter}
              onChange={(e) => setSkuFilter(e.target.value)}
            />
          </div>
        </div>

        {list.isLoading ? (
          <div className="px-4 py-6 text-sm text-ink-secondary">Загрузка…</div>
        ) : list.data && list.data.length > 0 ? (
          <div className="overflow-auto">
            <table className="table-shell min-w-[1000px] w-full text-sm">
              <thead>
                <tr>
                  <th className="px-3 py-2">SKU</th>
                  <th className="px-3 py-2">С даты</th>
                  <th className="px-3 py-2">Себестоимость</th>
                  <th className="px-3 py-2">Упаковка</th>
                  <th className="px-3 py-2">Логистика</th>
                  <th className="px-3 py-2">Доп.</th>
                  <th className="px-3 py-2">Итого</th>
                  <th className="px-3 py-2">Валюта</th>
                </tr>
              </thead>
              <tbody>
                {list.data.map((row) => (
                  <tr key={row.id}>
                    <td className="px-3 py-2 font-medium text-ink-secondary">{row.internal_sku}</td>
                    <td className="px-3 py-2 text-ink-muted">{fmtDate(row.effective_from)}</td>
                    <td className="px-3 py-2">{renderEditable(row, "product_cost")}</td>
                    <td className="px-3 py-2">{renderEditable(row, "packaging_cost")}</td>
                    <td className="px-3 py-2">{renderEditable(row, "inbound_logistics_cost")}</td>
                    <td className="px-3 py-2">{renderEditable(row, "additional_cost")}</td>
                    <td className="px-3 py-2 font-medium">{displayCost(row.cost)}</td>
                    <td className="px-3 py-2 text-ink-muted">{row.currency}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-4 py-10 text-center">
            <div className="text-sm font-medium">Себестоимость ещё не загружена</div>
            <div className="mt-1 text-xs text-ink-muted">
              {viewMode === "as_of"
                ? `Нет записей, действующих на ${fmtDate(viewDate)}.`
                : "Импортируйте CSV/Excel, чтобы расчёт прибыли и маржи стал корректнее."}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
