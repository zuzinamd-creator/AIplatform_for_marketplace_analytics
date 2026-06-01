export type SavedView = {
  id: string;
  name: string;
  page: "reports" | "recommendations";
  filter: Record<string, string>;
};

const KEY = "ma.savedViews";

export function loadSavedViews(page?: SavedView["page"]): SavedView[] {
  const raw = localStorage.getItem(KEY);
  const all: SavedView[] = raw ? (JSON.parse(raw) as SavedView[]) : [];
  return page ? all.filter((v) => v.page === page) : all;
}

export function saveView(view: Omit<SavedView, "id">) {
  const all = loadSavedViews();
  const next: SavedView = { ...view, id: crypto.randomUUID() };
  localStorage.setItem(KEY, JSON.stringify([next, ...all].slice(0, 20)));
  return next;
}

export function deleteView(id: string) {
  localStorage.setItem(KEY, JSON.stringify(loadSavedViews().filter((v) => v.id !== id)));
}
