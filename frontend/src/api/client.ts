/**
 * Client for the local Python service.
 *
 * In a packaged build the Rust shell spawns the service and gives us its URL and
 * auth token via the `backend_info` command. Running in a plain browser (vite
 * dev without the Tauri window) we fall back to the well-known dev address.
 */

const DEV_FALLBACK = { base_url: "http://127.0.0.1:8765", token: "", managed: false };

export type BackendInfo = { base_url: string; token: string; managed: boolean };

let cached: Promise<BackendInfo> | null = null;

function resolveBackend(): Promise<BackendInfo> {
  cached ??= (async () => {
    // `__TAURI_INTERNALS__` is present only inside the Tauri webview.
    if (!("__TAURI_INTERNALS__" in window)) return DEV_FALLBACK;
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      return await invoke<BackendInfo>("backend_info");
    } catch {
      return DEV_FALLBACK;
    }
  })();
  return cached;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const backend = await resolveBackend();
  const headers = new Headers(init?.headers);
  if (backend.token) headers.set("X-Kazu-Token", backend.token);

  const res = await fetch(`${backend.base_url}${path}`, { ...init, headers });
  if (!res.ok) {
    // FastAPI puts the useful part in `detail`; fall back to the status text.
    const detail = await res
      .json()
      .then((b) => b?.detail)
      .catch(() => null);
    throw new ApiError(detail ?? res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}
