import { StatusBadge } from "./status-badge";
import { t } from "../i18n";

export function AiTrustPanel(props: {
  trust?: {
    confidence_explanation?: string;
    limitations?: string[];
    urgency?: string;
    stale_data_note?: string | null;
    advisory_only?: boolean;
    seller_workflow_state?: string;
  };
}) {
  const trust = props.trust ?? {};
  const limitations = trust.limitations ?? [];

  return (
    <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 text-xs text-ink-secondary">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium text-amber-100/90">{t("trust.trust_transparency")}</span>
        {trust.advisory_only !== false ? <StatusBadge tone="warn">{t("trust.advisory_only")}</StatusBadge> : null}
        {trust.urgency ? <StatusBadge tone="info">{t("trust.urgency")}: {trust.urgency}</StatusBadge> : null}
      </div>
      {trust.confidence_explanation ? (
        <p className="mt-2 text-ink-secondary">{trust.confidence_explanation}</p>
      ) : null}
      {trust.stale_data_note ? <p className="mt-2 text-amber-200/80">{trust.stale_data_note}</p> : null}
      {limitations.length > 0 ? (
        <ul className="mt-2 list-inside list-disc text-ink-muted">
          {limitations.slice(0, 5).map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-ink0">
          AI не меняет карточки, цены и рекламу автоматически. Все KPI рассчитаны по вашим загруженным отчётам.
        </p>
      )}
    </div>
  );
}
