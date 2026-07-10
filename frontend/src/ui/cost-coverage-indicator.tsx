import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import { COST_COVERAGE_ROUTE, COSTS_WORKFLOW_ROUTE } from "../state/profit-trust";
import { formatMetric, formatPct, parseNumeric } from "../utils/format";
import { cx } from "./cx";

type Props = {
  coveredSkus: number;
  totalSkus: number;
  coveragePct: number | string | null;
  variant?: "pill" | "ring" | "bar";
  showCta?: boolean;
  ctaHref?: string;
  ctaLabel?: string;
  onClick?: () => void;
  className?: string;
};

function coverageTone(pct: number | null): "ok" | "warn" | "bad" {
  if (pct === null) return "bad";
  if (pct >= 100) return "ok";
  if (pct >= 1) return "warn";
  return "bad";
}

function toneClasses(tone: "ok" | "warn" | "bad"): string {
  switch (tone) {
    case "ok":
      return "border-emerald-200 bg-semantic-success-bg text-semantic-success";
    case "warn":
      return "border-amber-200 bg-semantic-warn-bg text-semantic-warn";
    case "bad":
      return "border-red-200 bg-semantic-danger-bg text-semantic-danger";
  }
}

function CtaLink(props: {
  href: string;
  label: string;
  onClick?: () => void;
  className?: string;
}) {
  if (props.onClick) {
    return (
      <button type="button" onClick={props.onClick} className={props.className}>
        {props.label}
        <ArrowRight className="ml-1 inline h-3 w-3" aria-hidden />
      </button>
    );
  }
  return (
    <Link to={props.href} className={props.className}>
      {props.label}
      <ArrowRight className="ml-1 inline h-3 w-3" aria-hidden />
    </Link>
  );
}

export function CostCoverageIndicator({
  coveredSkus,
  totalSkus,
  coveragePct,
  variant = "pill",
  showCta = false,
  ctaHref = COSTS_WORKFLOW_ROUTE,
  ctaLabel = "Загрузить себестоимость",
  onClick,
  className,
}: Props) {
  const pctValue = parseNumeric(coveragePct);
  const tone = coverageTone(pctValue);
  const pctLabel = formatPct(coveragePct);
  const skuLabel = `${formatMetric(coveredSkus, { suffix: "" })} / ${formatMetric(totalSkus, { suffix: "" })} SKU`;

  const ctaClass =
    "inline-flex items-center text-xs font-medium underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40";

  if (variant === "bar") {
    const width = pctValue !== null ? Math.min(100, Math.max(0, pctValue)) : 0;
    return (
      <div className={cx("space-y-2", className)} aria-label={`Покрытие себестоимости: ${pctLabel}, ${skuLabel}`}>
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="font-medium text-ink-secondary">Покрытие себестоимости</span>
          <span className="text-ink-muted">
            {pctLabel} · {skuLabel}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-surface-inset ring-1 ring-surface-subtle">
          <div
            className={cx(
              "h-full rounded-full transition-all",
              tone === "ok" && "bg-emerald-500",
              tone === "warn" && "bg-amber-500",
              tone === "bad" && "bg-red-500",
            )}
            style={{ width: `${width}%` }}
            role="progressbar"
            aria-valuenow={width}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Покрытие ${pctLabel}`}
          />
        </div>
        {showCta ? (
          <CtaLink href={ctaHref} label={ctaLabel} onClick={onClick} className={ctaClass} />
        ) : null}
      </div>
    );
  }

  if (variant === "ring") {
    return (
      <div
        className={cx(
          "flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between",
          toneClasses(tone),
          className,
        )}
        aria-label={`Покрытие себестоимости: ${pctLabel}`}
      >
        <div>
          <div className="text-sm font-semibold">Себестоимость: {pctLabel}</div>
          <div className="mt-1 text-xs opacity-90">
            {skuLabel} с продажами в периоде
          </div>
        </div>
        {showCta ? (
          <CtaLink
            href={ctaHref}
            label={ctaLabel}
            onClick={onClick}
            className={cx(ctaClass, "shrink-0")}
          />
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={cx(
        "inline-flex flex-wrap items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium",
        toneClasses(tone),
        className,
      )}
      aria-label={`Покрытие себестоимости: ${pctLabel}, ${skuLabel}`}
    >
      <span>Себестоимость {pctLabel}</span>
      <span className="opacity-80">({skuLabel})</span>
      {showCta ? (
        <CtaLink
          href={ctaHref}
          label={ctaLabel}
          onClick={onClick}
          className={cx(ctaClass, "ml-1")}
        />
      ) : null}
    </div>
  );
}

export { COST_COVERAGE_ROUTE, COSTS_WORKFLOW_ROUTE };
