import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";

import { FEATURE_FLAGS } from "../state/feature-flags";
import {
  COST_COVERAGE_ROUTE,
  COSTS_WORKFLOW_ROUTE,
  profitTrustLabel,
  type ProfitTrustLevel,
} from "../state/profit-trust";
import { formatMetric, formatPct } from "../utils/format";
import { Card } from "./card";
import { cx } from "./cx";
import { StatusBadge } from "./status-badge";

const DISMISS_PREFIX = "ma.costTrustBanner.dismissed.";

type BannerTone = "ok" | "warn" | "bad";

type Props = {
  trust: ProfitTrustLevel;
  variant?: "global" | "inline" | "compact";
  coveragePct?: number | string | null;
  coveredSkus?: number | null;
  totalSkus?: number | null;
  missingSkusSample?: string[];
  dismissible?: boolean;
  storageKey?: string;
  costsHref?: string;
  coverageHref?: string;
  className?: string;
};

function toneForTrust(trust: ProfitTrustLevel): BannerTone {
  switch (trust) {
    case "full":
      return "ok";
    case "partial":
      return "warn";
    case "insufficient":
      return "bad";
  }
}

function cardToneClass(tone: BannerTone): string {
  switch (tone) {
    case "ok":
      return "border-emerald-200 bg-semantic-success-bg";
    case "warn":
      return "border-amber-200 bg-semantic-warn-bg";
    case "bad":
      return "border-red-200 bg-semantic-danger-bg";
  }
}

function readDismissed(storageKey: string): boolean {
  try {
    return sessionStorage.getItem(DISMISS_PREFIX + storageKey) === "1";
  } catch {
    return false;
  }
}

function writeDismissed(storageKey: string): void {
  try {
    sessionStorage.setItem(DISMISS_PREFIX + storageKey, "1");
  } catch {
    // ignore storage failures
  }
}

function buildMessage(
  trust: ProfitTrustLevel,
  coveragePct: number | string | null | undefined,
  coveredSkus: number | null | undefined,
  totalSkus: number | null | undefined,
  missingSkusSample: string[],
): string {
  if (trust === "full") {
    return "Себестоимость покрывает все продаваемые SKU — прибыль и маржа отображаются как проверенные.";
  }
  if (trust === "insufficient") {
    return "Прибыль и маржа недоступны без себестоимости. Загрузите cost-данные, чтобы включить финансовые KPI.";
  }

  const pct = formatPct(coveragePct ?? null);
  const sku =
    coveredSkus != null && totalSkus != null
      ? `${formatMetric(coveredSkus)} из ${formatMetric(totalSkus)} SKU`
      : null;
  const missing =
    missingSkusSample.length > 0
      ? ` Примеры без cost: ${missingSkusSample.slice(0, 5).join(", ")}.`
      : "";
  return `Себестоимость: ${pct}${sku ? ` (${sku})` : ""} — прибыль может быть неточной, маржа скрыта.${missing}`;
}

export function CostTrustBanner({
  trust,
  variant = "inline",
  coveragePct,
  coveredSkus,
  totalSkus,
  missingSkusSample = [],
  dismissible = true,
  storageKey = `cost-trust-${trust}`,
  costsHref = COSTS_WORKFLOW_ROUTE,
  coverageHref = COST_COVERAGE_ROUTE,
  className,
}: Props) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (dismissible) {
      setDismissed(readDismissed(storageKey));
    }
  }, [dismissible, storageKey]);

  const onDismiss = useCallback(() => {
    writeDismissed(storageKey);
    setDismissed(true);
  }, [storageKey]);

  if (trust === "full" || dismissed) {
    return null;
  }

  const tone = toneForTrust(trust);
  const title = profitTrustLabel(trust);
  const message = buildMessage(trust, coveragePct, coveredSkus ?? null, totalSkus ?? null, missingSkusSample);

  const isCompact = variant === "compact";
  const isGlobal = variant === "global";

  return (
    <Card
      className={cx(
        cardToneClass(tone),
        isCompact ? "p-3" : "p-4",
        isGlobal && "shadow-soft",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <div className={cx("flex gap-3", isCompact ? "items-start" : "flex-col md:flex-row md:items-center md:justify-between")}>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={tone}>{title}</StatusBadge>
            {!isCompact ? (
              <span className="text-xs font-medium text-ink-muted">Доверие к прибыли</span>
            ) : null}
          </div>
          <p className={cx("leading-relaxed text-ink-secondary", isCompact ? "mt-1.5 text-xs" : "mt-1.5 text-sm")}>
            {message}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Link to={costsHref} className="btn-secondary h-9 px-3 text-xs">
            Загрузить себестоимость
          </Link>
          {!isCompact ? (
            <Link to={coverageHref} className="btn-secondary h-9 px-3 text-xs">
              Покрытие cost
            </Link>
          ) : null}
          {dismissible ? (
            <button
              type="button"
              onClick={onDismiss}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-ink-muted transition hover:bg-surface/60 hover:text-ink"
              aria-label="Скрыть предупреждение до конца сессии"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </div>
    </Card>
  );
}

/**
 * AppShell mounting point for the global cost trust banner.
 * Disabled by default via FEATURE_FLAGS until Phase 9.6B-2 wires live integrity data.
 */
export function CostTrustBannerMount() {
  if (!FEATURE_FLAGS.costTrustBannerGlobal) {
    return null;
  }

  // Phase 9.6B-2: fetch dashboard integrity / cost coverage and render CostTrustBanner variant="global".
  return null;
}
