// Backend access goes through the Vite dev proxy (see vite.config.js),
// so relative paths work in Docker without CORS.
export async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(body?.detail?.error || `HTTP ${res.status}`);
    err.detail = body?.detail;
    throw err;
  }
  return body;
}

export function liveSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${proto}://${location.host}/v0/live`);
}
