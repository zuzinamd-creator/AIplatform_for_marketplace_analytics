import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { Label, Select } from "../../ui/field";

const statusOptions = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "succeeded", label: "Succeeded" },
  { value: "failed", label: "Failed" },
  { value: "deferred", label: "Deferred" },
];

export function RebuildsPage() {
  const [status, setStatus] = useState("");
  const q = useQuery({
    queryKey: ["ops", "rebuilds", 0, 50, status],
    queryFn: () => api.ops.rebuilds(0, 50, status || undefined),
  });

  const items = (q.data as any)?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Rebuild lifecycle</div>
        <div className="text-sm text-slate-300">Visibility into snapshot rebuild requirements and dispatch outcomes.</div>
      </div>

      <Card className="p-5">
        <div className="max-w-xs space-y-1.5">
          <Label>Status</Label>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            {statusOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>

        <div className="mt-4">
          {q.isLoading ? (
            <div className="text-sm text-slate-300">Loading…</div>
          ) : (
            <pre className="overflow-auto text-[11px] text-slate-300">{JSON.stringify(items, null, 2)}</pre>
          )}
        </div>
      </Card>
    </div>
  );
}

