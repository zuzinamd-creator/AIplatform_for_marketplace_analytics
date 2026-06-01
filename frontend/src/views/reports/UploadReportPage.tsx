import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";

import { api, formatApiError } from "../../state/http";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { Label, Select } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";
import { toast } from "../../ui/toast";

const marketplaces = [
  { value: "wildberries", label: "Wildberries" },
  { value: "ozon", label: "Ozon" },
];

const reportTypes = [
  { value: "finance", label: "Финансы (WB еженедельный .xlsx)" },
  { value: "sales", label: "Продажи" },
  { value: "orders", label: "Заказы" },
  { value: "stock", label: "Остатки" },
  { value: "other", label: "Другое" },
];

function friendlyUploadError(raw: string): { title: string; body: string } {
  const m = raw.match(/^\[([a-z0-9_]+)\]\s*(.*)$/i);
  if (!m) return { title: "Ошибка загрузки", body: raw };
  const code = m[1]!.toLowerCase();
  const rest = m[2] ?? raw;
  if (code === "wb_excel_unrecognized") {
    return {
      title: "Не удалось распознать отчёт Wildberries",
      body: rest,
    };
  }
  if (code === "invalid_values") {
    return {
      title: "Есть ошибки в данных файла",
      body: rest,
    };
  }
  return { title: "Ошибка загрузки", body: rest };
}

export function UploadReportPage() {
  const qc = useQueryClient();
  const [marketplace, setMarketplace] = useState(marketplaces[0]!.value);
  const [reportType, setReportType] = useState("finance");
  const [progress, setProgress] = useState<number>(0);
  const [picked, setPicked] = useState<File | null>(null);

  const coverage = useQuery({
    queryKey: ["analytics", "coverage"],
    queryFn: () => api.analytics.coverage(),
  });

  const upload = useMutation({
    mutationFn: async () => {
      if (!picked) throw new Error("Сначала выберите файл.");
      const form = new FormData();
      form.set("marketplace", marketplace);
      form.set("report_type", reportType);
      form.set("file", picked);
      return await api.reports.upload(form, (pct) => setProgress(pct));
    },
    onSuccess: async (res) => {
      toast("Файл принят", res.message);
      setProgress(0);
      setPicked(null);
      await qc.invalidateQueries({ queryKey: ["reports"] });
      await qc.invalidateQueries({ queryKey: ["ops", "queue"] });
      await qc.invalidateQueries({ queryKey: ["analytics", "coverage"] });
    },
    onError: (err) => {
      const raw = formatApiError(err);
      const msg = friendlyUploadError(raw);
      toast(msg.title, msg.body);
    },
  });

  const dz = useDropzone({
    multiple: false,
    accept: {
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "text/csv": [".csv"],
    },
    onDrop: (files) => setPicked(files[0] ?? null),
  });

  const hint = useMemo(() => {
    if (!picked) return "Перетащите отчёт сюда (.xlsx / .csv).";
    return `${picked.name} • ${(picked.size / 1024 / 1024).toFixed(2)} MB`;
  }, [picked]);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Загрузка отчёта</div>
        <div className="text-sm text-slate-300">Загрузка с диагностикой ошибок и подсказками по полноте данных.</div>
      </div>

      <Card className="p-5">
        <div className="text-sm font-semibold">Что нужно загрузить для более точного анализа</div>
        <div className="mt-2 text-xs text-slate-400">
          Подсказки формируются детерминированно по покрытию данных и предупреждениям целостности.
        </div>
        <div className="mt-3 space-y-2">
          {(coverage.data?.recommendations ?? []).slice(0, 6).map((r) => (
            <div key={r.code} className="rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-medium text-slate-200">{r.title}</div>
                <StatusBadge tone={r.severity === "warning" ? "warn" : r.severity === "critical" ? "bad" : "info"}>
                  {r.severity}
                </StatusBadge>
              </div>
              <div className="mt-1 text-xs text-slate-300">{r.message}</div>
            </div>
          ))}
          {coverage.data && !(coverage.data.recommendations?.length ?? 0) ? (
            <div className="text-sm text-slate-400">Пока нет рекомендаций по загрузке — покрытие выглядит достаточным.</div>
          ) : null}
        </div>
      </Card>

      <Card className="p-5">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Маркетплейс</Label>
            <Select value={marketplace} onChange={(e) => setMarketplace(e.target.value)}>
              {marketplaces.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Тип отчёта</Label>
            <Select value={reportType} onChange={(e) => setReportType(e.target.value)}>
              {reportTypes.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div
          {...dz.getRootProps()}
          className="mt-5 cursor-pointer rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-8 text-center"
          role="button"
          tabIndex={0}
          aria-label="Зона загрузки отчёта"
        >
          <input {...dz.getInputProps()} />
          <div className="text-sm font-medium">{hint}</div>
          <div className="mt-1 text-xs text-slate-400">
            Бэкенд валидирует контент и при совпадении checksum вернет уже загруженный отчёт.
          </div>
        </div>

        {upload.isPending ? (
          <div className="mt-4 flex items-center justify-between gap-3">
            <div className="text-sm text-slate-200">Загрузка…</div>
            <StatusBadge tone="info">{progress}%</StatusBadge>
          </div>
        ) : null}

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <Button disabled={!picked || upload.isPending} onClick={() => upload.mutate()}>
            {upload.isPending ? "Загрузка…" : "Загрузить"}
          </Button>
          <Button
            variant="ghost"
            disabled={upload.isPending}
            onClick={() => {
              setPicked(null);
              setProgress(0);
            }}
          >
            Сбросить
          </Button>
        </div>
      </Card>
    </div>
  );
}

