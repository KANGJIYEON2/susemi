/**
 * Admin token localStorage 래퍼.
 *
 * - 키: "susemi.admin_token"
 * - 백엔드는 X-Admin-Token 헤더로 받음 (server/app/security.py)
 * - SSR 안전 (typeof window 가드)
 */

const STORAGE_KEY = "susemi.admin_token";

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAdminToken(token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, token);
  } catch {
    /* private browsing 등 — 무시 */
  }
}

export function clearAdminToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
