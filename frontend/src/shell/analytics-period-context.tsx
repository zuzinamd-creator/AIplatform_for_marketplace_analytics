import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { loadPeriodSelection, savePeriodSelection, type PeriodSelection } from "../state/period";

type AnalyticsPeriodContextValue = {
  periodSel: PeriodSelection;
  setPeriodSel: React.Dispatch<React.SetStateAction<PeriodSelection>>;
};

const AnalyticsPeriodContext = createContext<AnalyticsPeriodContextValue | null>(null);

export function AnalyticsPeriodProvider({ children }: { children: ReactNode }) {
  const [periodSel, setPeriodSel] = useState<PeriodSelection>(() => loadPeriodSelection());

  useEffect(() => {
    savePeriodSelection(periodSel);
  }, [periodSel]);

  const value = useMemo(() => ({ periodSel, setPeriodSel }), [periodSel]);

  return <AnalyticsPeriodContext.Provider value={value}>{children}</AnalyticsPeriodContext.Provider>;
}

export function useAnalyticsPeriod(): AnalyticsPeriodContextValue | null {
  return useContext(AnalyticsPeriodContext);
}
