import { useState } from "react";

import { useAnalyticsPeriod } from "../shell/analytics-period-context";
import { loadPeriodSelection, type PeriodSelection } from "./period";

/** Hub tabs share AnalyticsPeriodProvider; standalone routes keep local period state. */
export function usePagePeriod(initializer?: () => PeriodSelection) {
  const analyticsPeriod = useAnalyticsPeriod();
  const [localPeriod, setLocalPeriod] = useState<PeriodSelection>(
    initializer ?? (() => loadPeriodSelection()),
  );

  if (analyticsPeriod) {
    return {
      periodSel: analyticsPeriod.periodSel,
      setPeriodSel: analyticsPeriod.setPeriodSel,
      inAnalyticsHub: true as const,
    };
  }

  return {
    periodSel: localPeriod,
    setPeriodSel: setLocalPeriod,
    inAnalyticsHub: false as const,
  };
}
