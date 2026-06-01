const KEY = "ma.firstRunChecklist.dismissed";

export function isFirstRunChecklistDismissed(): boolean {
  return localStorage.getItem(KEY) === "1";
}

export function dismissFirstRunChecklist(): void {
  localStorage.setItem(KEY, "1");
}

