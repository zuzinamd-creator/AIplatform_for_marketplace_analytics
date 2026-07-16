import { Card } from "../../ui/card";
import type { BusinessSignal } from "./business-signals";

export type BusinessSignalsPanelProps = {
  signals: BusinessSignal[];
};

export function BusinessSignalsPanel({ signals }: BusinessSignalsPanelProps) {
  if (signals.length === 0) return null;

  return (
    <Card className="p-5" data-testid="business-signals-panel">
      <div className="text-sm font-semibold text-ink">Бизнес-сигналы</div>
      <ul className="mt-3 space-y-2">
        {signals.map((signal) => (
          <li
            key={signal.id}
            data-testid={`business-signal-${signal.id}`}
            className="rounded-lg border border-surface-subtle/80 bg-surface-inset/60 px-3 py-2 text-sm text-ink-secondary"
          >
            {signal.text}
          </li>
        ))}
      </ul>
    </Card>
  );
}
