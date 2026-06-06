export const SESSION_EXPIRED_KEY = "ma.sessionExpired";

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

export function handleUnauthorized() {
  unauthorizedHandler?.();
}
