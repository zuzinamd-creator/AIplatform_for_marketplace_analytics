import { RU } from "./ru";

export const i18n = {
  ru: RU,
} as const;

type Dict = typeof RU;

function get(obj: any, path: string): unknown {
  const parts = path.split(".");
  let cur: any = obj;
  for (const p of parts) {
    cur = cur?.[p];
  }
  return cur;
}

export function t(key: string): string {
  const val = get(RU as Dict, key);
  return typeof val === "string" ? val : key;
}

