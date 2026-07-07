import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { api } from "../../state/http";
import type { ReportResponse } from "../../state/types-reports";
import { formatRub } from "../../utils/format";
import { toast } from "../../ui/toast";

function parseAmount(raw: string): number {
  const normalized = raw.replace(/\s/g, "").replace(",", ".").trim();
  if (!normalized) return 0;
  const value = Number(normalized);
  if (!Number.isFinite(value) || value < 0) return NaN;
  return value;
}

type Props = {
  report: ReportResponse;
};

export function PromotionExpensesCell({ report }: Props) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const processed = String(report.status).toLowerCase().includes("processed");
  const current = Number(report.promotion_expenses ?? "0");

  const save = useMutation({
    mutationFn: (value: number) =>
      api.reports.patch(report.id, { promotion_expenses: value.toFixed(2) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setEditing(false);
    },
    onError: (error: Error) => {
      toast("Не удалось сохранить", error.message || undefined);
    },
  });

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  if (!processed) {
    return <span className="text-ink-muted">—</span>;
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        className="w-full rounded border border-surface-subtle bg-surface px-2 py-1 text-sm"
        value={draft}
        disabled={save.isPending}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          if (e.key === "Escape") {
            setEditing(false);
            setDraft(String(current));
          }
        }}
        onBlur={() => {
          const value = parseAmount(draft);
          if (Number.isNaN(value)) {
            toast("Введите число ≥ 0");
            setDraft(String(current));
            setEditing(false);
            return;
          }
          if (value === current) {
            setEditing(false);
            return;
          }
          save.mutate(value);
        }}
      />
    );
  }

  return (
    <button
      type="button"
      className="w-full truncate text-left text-ink-secondary hover:underline"
      title="Нажмите, чтобы изменить"
      onClick={(e) => {
        e.preventDefault();
        setDraft(current > 0 ? String(current) : "");
        setEditing(true);
      }}
    >
      {save.isPending ? "…" : formatRub(current)}
    </button>
  );
}
