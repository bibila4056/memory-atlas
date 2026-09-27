import type { components } from "./api-schema";

export type CaptureSession = components["schemas"]["CaptureSession"];
export type SourceFragment = components["schemas"]["SourceFragment"];
export type FragmentPreferences = components["schemas"]["FragmentPreferences"];
export const SESSION_KEY = "memory-atlas.capture-session";
export const OPENED_KEY = "memory-atlas.diary-opened";

export async function captureRequest<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options).catch(() => null);
  if (!response) throw new Error("Your notebook can’t reach its server. Check that it’s running, then try again. Nothing you added is lost.");
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    if (typeof error?.detail === "string") throw new Error(error.detail);
    // The Next proxy answers 500/502/504 with a non-JSON page when the API process is down.
    throw new Error(response.status >= 500 ? "The notebook’s server isn’t running right now (start it with npm run dev:api). Nothing you added is lost." : "We couldn’t save that. Please try again.");
  }
  return response.json();
}

export async function restoreSession(): Promise<CaptureSession> {
  const requested = new URL(window.location.href).searchParams.get("session");
  if (requested && /^[0-9a-f-]{36}$/i.test(requested)) localStorage.setItem(SESSION_KEY, requested);
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  const open = (session_id: string) => captureRequest<CaptureSession>("/api/session", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id }),
  });
  const session = await open(id);
  // A remembered session that has already been woven is finished: Capture starts a brand-new page.
  // (An explicit ?session=… link still reopens it on purpose.)
  if (session.woven && !requested) {
    const fresh = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, fresh);
    return open(fresh);
  }
  return session;
}

export async function ingestFragments(sessionId: string, files: File[] = [], text?: string): Promise<CaptureSession> {
  const data = new FormData();
  data.set("session_id", sessionId);
  files.forEach((file) => data.append("files", file));
  if (text !== undefined) data.set("text_json", JSON.stringify(text));
  return captureRequest<CaptureSession>("/api/ingest", { method: "POST", body: data });
}
