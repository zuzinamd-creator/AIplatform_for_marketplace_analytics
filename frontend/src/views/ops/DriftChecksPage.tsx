import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { Label, Select } from "../../ui/field";

export function DriftChecksPage() {
  const [mode, setMode] = useState<"all" | "consistent">("all");
  const q = useQuery({
    queryKey: ["ops", "driftChecks", 0, 50, mode],
    queryFn: () => api.ops.driftChecks(0, 50, mode === "consistent" ? true : undefined),
  });

  const items = (q.data as any)?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Drift indicators</div>
        <div className="text-sm text-ink-secondary">
          Read-only drift checks for inventory/snapshot consistency (staleness and rebuild signals).
        </div>
      </div>

      <Card className="p-5">
        <div className="max-w-xs space-y-1.5">
          <Label>Filter</Label>
          <Select value={mode} onChange={(e) => setMode(e.target.value as any)}>
            <option value="all">All</option>
            <option value="consistent">Consistent only</option>
          </Select>
        </div>

        <div className="mt-4">
          {q.isLoading ? (
            <div className="text-sm text-ink-secondary">Loading…</div>
          ) : (
            <pre className="overflow-auto text-[11px] text-ink-secondary">{JSON.stringify(items, null, 2)}</pre>
          )}
        </div>
      </Card>
    </div>
  );
}

