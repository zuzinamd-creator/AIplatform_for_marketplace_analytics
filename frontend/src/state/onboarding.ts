export type WorkspaceProfile = {
  workspace_name: string;
  marketplace: "wildberries" | "ozon" | "unknown";
};

const KEY_PROFILE = "ma.workspaceProfile";
const KEY_ONBOARDING_DONE = "ma.onboardingDone";

export function loadWorkspaceProfile(): WorkspaceProfile {
  const raw = localStorage.getItem(KEY_PROFILE);
  if (!raw) return { workspace_name: "My workspace", marketplace: "unknown" };
  try {
    return JSON.parse(raw) as WorkspaceProfile;
  } catch {
    return { workspace_name: "My workspace", marketplace: "unknown" };
  }
}

export function saveWorkspaceProfile(p: WorkspaceProfile) {
  localStorage.setItem(KEY_PROFILE, JSON.stringify(p));
}

export function isOnboardingDone() {
  return localStorage.getItem(KEY_ONBOARDING_DONE) === "true";
}

export function setOnboardingDone(done: boolean) {
  localStorage.setItem(KEY_ONBOARDING_DONE, done ? "true" : "false");
}

