/** Scroll to a dashboard hash target (React Router does not auto-scroll same-route hashes). */

export function scrollToHashTarget(hash: string, behavior: ScrollBehavior = "smooth"): boolean {
  const id = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!id) return false;
  const el = document.getElementById(id);
  if (!el) return false;
  el.scrollIntoView({ behavior, block: "start" });
  return true;
}

/** Parse `path#hash` hrefs used by Action Strip CTAs. */
export function splitPathAndHash(href: string): { pathname: string; hash: string } {
  const idx = href.indexOf("#");
  if (idx === -1) {
    return { pathname: href, hash: "" };
  }
  return { pathname: href.slice(0, idx), hash: href.slice(idx) };
}
