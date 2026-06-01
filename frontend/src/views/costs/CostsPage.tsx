import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";

import { api, formatApiError } from "../../state/http";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { StatusBadge } from "../../ui/status-badge";
import { toast } from "../../ui/toast";

export function CostsPage() {
  const qc = useQueryClient();
  const [picked, setPicked] = useState<File | null>(null);
  const [showPreview, setShowPreview] = useState(true);

  const list = useQuery({
    queryKey: ["costs", "list"],
    queryFn: () => api.costs.list(),
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

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Себестоимость</div>
        <div className="text-sm text-slate-300">
          Импортируйте себестоимость по SKU. Это включает расчёт прибыли/маржи и улучшает качество рекомендаций AI.
        </div>
      </div>

      <Card className="p-5">
        <div
          {...dz.getRootProps()}
          className="cursor-pointer rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-8 text-center"
          role="button"
          tabIndex={0}
          aria-label="Зона импорта себестоимости"
        >
          <input {...dz.getInputProps()} />
          <div className="text-sm font-medium">{hint}</div>
          <div className="mt-1 text-xs text-slate-400">
            Совет: используйте шаблон и заполняйте себестоимость в одной валюте.
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            disabled={downloadTemplate.isPending}
            onClick={() => downloadTemplate.mutate()}
          >
            {downloadTemplate.isPending ? "Скачивание…" : "Скачать шаблон для заполнения"}
          </Button>
          <Button disabled={!picked || imp.isPending} onClick={() => imp.mutate()}>
            {imp.isPending ? "Импорт…" : "Импортировать себестоимость"}
          </Button>
          <Button
            variant="ghost"
            disabled={imp.isPending}
            onClick={() => {
              setPicked(null);
            }}
          >
            Сбросить
          </Button>
        </div>

        {picked && preview.data ? (
          <div className="mt-4 rounded-lg border border-slate-800/70 bg-slate-950/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">Проверка файла перед импортом</div>
                <div className="mt-1 text-xs text-slate-400">
                  Строк в файле: {preview.data.total_rows}. Показаны первые {preview.data.preview_rows.length}.
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowPreview((v) => !v)}>
                {showPreview ? "Скрыть превью" : "Показать превью"}
              </Button>
            </div>

            {(preview.data.issues ?? []).length ? (
              <div className="mt-3 space-y-1 text-xs text-slate-300">
                {preview.data.issues.slice(0, 8).map((it, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <StatusBadge tone={it.severity === "error" ? "bad" : "warn"}>{it.code}</StatusBadge>
                    <div className="text-slate-200">
                      {it.message}
                      {it.row_index != null ? <span className="text-slate-500"> (строка {it.row_index})</span> : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 text-xs text-slate-400">Ошибок структуры не найдено. Можно импортировать.</div>
            )}

            <div className="mt-3 overflow-auto">
              <table className="min-w-[880px] text-left text-xs">
                <thead className="text-slate-400">
                  <tr>
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-3">SKU</th>
                    <th className="py-2 pr-3">Дата</th>
                    <th className="py-2 pr-3">Себестоимость</th>
                    <th className="py-2 pr-3">Упаковка</th>
                    <th className="py-2 pr-3">Логистика</th>
                    <th className="py-2 pr-3">Доп.</th>
                    <th className="py-2 pr-3">Итого</th>
                    <th className="py-2 pr-3">Валюта</th>
                  </tr>
                </thead>
                <tbody className="text-slate-200">
                  {preview.data.preview_rows.map((r) => (
                    <tr key={r.row_index} className="border-t border-slate-900/60">
                      <td className="py-2 pr-3 text-slate-500">{r.row_index}</td>
                      <td className="py-2 pr-3">{r.internal_sku ?? "—"}</td>
                      <td className="py-2 pr-3">{r.effective_from ?? "—"}</td>
                      <td className="py-2 pr-3">{r.product_cost ?? "—"}</td>
                      <td className="py-2 pr-3">{r.packaging_cost ?? "—"}</td>
                      <td className="py-2 pr-3">{r.inbound_logistics_cost ?? "—"}</td>
                      <td className="py-2 pr-3">{r.additional_cost ?? "—"}</td>
                      <td className="py-2 pr-3">{r.total_cost ?? "—"}</td>
                      <td className="py-2 pr-3">{r.currency ?? "RUB"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : picked && preview.isLoading ? (
          <div className="mt-4 text-xs text-slate-400">Проверяем файл…</div>
        ) : picked && preview.isError ? (
          <div className="mt-4 text-xs text-rose-300">Не удалось проверить файл: {formatApiError(preview.error)}</div>
        ) : null}
      </Card>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800/70 bg-slate-950/40 px-4 py-3">
          <div className="text-sm font-semibold">Текущая себестоимость</div>
          <StatusBadge tone="info">{list.isLoading ? "…" : `${list.data?.length ?? 0} строк`}</StatusBadge>
        </div>
        {list.isLoading ? (
          <div className="px-4 py-6 text-sm text-slate-300">Загрузка…</div>
        ) : list.data && list.data.length > 0 ? (
          <pre className="max-h-[420px] overflow-auto px-4 py-4 text-[11px] text-slate-300">
            {JSON.stringify(list.data.slice(0, 50), null, 2)}
          </pre>
        ) : (
          <div className="px-4 py-10 text-center">
            <div className="text-sm font-medium">Себестоимость ещё не загружена</div>
            <div className="mt-1 text-xs text-slate-400">
              Импортируйте CSV/Excel, чтобы расчёт прибыли и маржи стал корректнее.
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

