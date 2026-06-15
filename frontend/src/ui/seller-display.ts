/** Seller-facing display helpers — labels and sanitization for AI recommendations. */

export function confidenceLabelRu(value: number | string | null | undefined): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  if (n > 1) {
    if (n >= 85) return "Высокая";
    if (n >= 65) return "Средняя";
    return "Низкая";
  }
  if (n >= 0.85) return "Высокая";
  if (n >= 0.65) return "Средняя";
  return "Низкая";
}

export function riskLabelRu(value: string | null | undefined): string {
  const map: Record<string, string> = {
    low: "Низкий",
    medium: "Средний",
    high: "Высокий",
    critical: "Критический",
  };
  if (!value) return "—";
  return map[String(value).toLowerCase()] ?? value;
}

export function priorityTierLabelRu(value: string | null | undefined): string {
  const map: Record<string, string> = {
    today: "Сделать сегодня",
    this_week: "На этой неделе",
    informational: "Информация",
    high: "Высокий",
    medium: "Средний",
    low: "Низкий",
  };
  if (!value) return "—";
  return map[String(value).toLowerCase()] ?? value;
}

export function workflowStateLabelRu(value: string | null | undefined): string {
  const map: Record<string, string> = {
    active: "Активна",
    saved: "В избранном",
    snoozed: "Отложена",
    completed: "Выполнена",
    dismissed: "Скрыта",
    waiting_for_data: "Жду данные",
    done_today: "На сегодня",
  };
  if (!value) return "—";
  return map[String(value).toLowerCase()] ?? value;
}

export function eventTypeLabelRu(value: string | null | undefined): string {
  const map: Record<string, string> = {
    note: "Заметка",
    complete: "Выполнено",
    save: "В избранное",
    snooze: "Отложено",
    dismiss: "Скрыто",
    reactivate: "Возобновлено",
    done_today: "На сегодня",
    waiting_for_data: "Жду данные",
  };
  if (!value) return "Событие";
  return map[String(value).toLowerCase()] ?? value;
}

export const FOLLOW_UP_CHIPS: Array<{ id: string; label: string }> = [
  { id: "why", label: "Почему" },
  { id: "impact", label: "Эффект" },
  { id: "action", label: "Действие" },
  { id: "confidence", label: "Уверенность" },
  { id: "evidence", label: "Доказательства" },
  { id: "limitations", label: "Ограничения" },
];

export type SellerDomainInsight = {
  insight_id?: string;
  domain?: string;
  statement?: string;
  why_it_matters?: string;
  recommended_actions?: string[];
  priority_rank?: number;
};

export const DEFAULT_SELLER_ACTION =
  "Сверьте KPI на Dashboard и выберите корректирующее действие по проблемным SKU.";

const ACTION_VERB_RE =
  /\b(проверьте|снизьте|увеличьте|пересмотрите|загрузите|оцените|проведите|сверьте|рассмотрите|импортируйте|скорректируйте|добавьте|оптимизируйте|остановите|диверсифицируйте|продвигайте)\b/i;

const ANALYTICS_START_RE =
  /^(выручка|прибыль|маржа|основной|главный|драйвер|концентрация|объём|объем|капитал|sku\s)/i;

/** Parse structured summary blocks for display when API returns legacy text. */
export function parseSellerSummarySections(summary: string): {
  headline: string;
  whatHappened: string;
  action: string;
  why: string;
  limitations: string;
  raw: string;
} {
  const raw = summary ?? "";
  const pick = (label: string, nextLabels: string[]) => {
    const start = raw.indexOf(`${label}:`);
    if (start < 0) return "";
    const after = raw.slice(start + label.length + 1);
    let end = after.length;
    for (const n of nextLabels) {
      const i = after.indexOf(`\n\n${n}:`);
      if (i >= 0) end = Math.min(end, i);
    }
    return after.slice(0, end).trim();
  };

  const pickMarkdown = (heading: string) => {
    const start = raw.indexOf(heading);
    if (start < 0) return "";
    const after = raw.slice(start + heading.length).replace(/^\s*\n+/, "");
    const next = after.search(/\n### /);
    return (next >= 0 ? after.slice(0, next) : after).trim();
  };

  const headline = pick("Главный вывод", ["Что произошло", "Что делать", "Почему это важно", "Ограничения анализа"]);
  const whatHappened = pick("Что произошло", ["Что делать", "Почему это важно", "Ограничения анализа"]);
  const action =
    pick("Что делать", ["Почему это важно", "Ограничения анализа"]) ||
    pick("Действие", ["Почему", "Уверенность", "Ограничения"]);
  const why =
    pick("Почему это важно", ["Ограничения анализа"]) || pick("Почему", ["Уверенность", "Действие", "Ограничения"]);
  const limitations =
    pick("Ограничения анализа", []) || pickMarkdown("### Ограничения анализа");

  if (!headline && !whatHappened) {
    return { headline: "", whatHappened: "", action: "", why: "", limitations: "", raw };
  }
  return { headline, whatHappened, action, why, limitations, raw };
}

/** Extract imperative-only sentences; expand combined «наличие, цену и рекламу» checks. */
export function extractSellerActions(text: string): string {
  const src = (text ?? "").trim();
  if (!src) return "";

  const imperativeRe =
    /\b((?:проверьте|снизьте|увеличьте|пересмотрите|загрузите|оцените|проведите|сверьте|рассмотрите|импортируйте|скорректируйте|добавьте|оптимизируйте|остановите|диверсифицируйте|продвигайте)[^.!?]*[.!?])/gi;

  const found: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = imperativeRe.exec(src)) !== null) {
    const sentence = m[1].trim();
    if (sentence && !found.includes(sentence)) found.push(sentence.endsWith(".") ? sentence : `${sentence}.`);
  }

  const skuMatch = src.match(/SKU\s+(\S+)/i);
  const sku = skuMatch?.[1];
  const expanded: string[] = [];
  for (const sentence of found) {
    const low = sentence.toLowerCase();
    if (low.includes("наличие") && low.includes("цен") && low.includes("реклам")) {
      const suffix = sku ? ` SKU ${sku}.` : ".";
      expanded.push(`Проверьте остатки${suffix}`, `Проверьте цену относительно конкурентов${suffix}`, `Проверьте рекламную активность товара${suffix}`);
    } else {
      expanded.push(sentence);
    }
  }

  if (expanded.length === 0) return "";
  if (expanded.length === 1) return expanded[0];
  return expanded.map((a, i) => `${i + 1}. ${a}`).join("\n");
}

/** True when text looks like an imperative seller action, not analytics. */
export function isSellerAction(text: string): boolean {
  const extracted = extractSellerActions(text);
  if (extracted) return true;
  const t = (text ?? "").trim();
  if (!t) return false;
  const firstLine = t.split("\n")[0].trim();
  if (ANALYTICS_START_RE.test(firstLine) && !ACTION_VERB_RE.test(firstLine)) return false;
  return ACTION_VERB_RE.test(t);
}

/** Prefer imperative actions only; never fall back to analytics copy. */
export function pickSellerAction(...candidates: Array<string | null | undefined>): string {
  for (const c of candidates) {
    const extracted = extractSellerActions(String(c ?? ""));
    if (extracted) return extracted;
  }
  return DEFAULT_SELLER_ACTION;
}
