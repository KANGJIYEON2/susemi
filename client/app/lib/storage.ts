/**
 * 분석 결과 + 입력값을 IndexedDB 에 저장하는 클라이언트 사이드 영속 레이어.
 *
 * 원칙:
 * - 서버에 보내지 않음. 사용자 디바이스에만 저장.
 * - 모든 메서드가 SSR/IndexedDB 미지원 환경에서도 안전하게 실패 (silent or 명시적 오류).
 * - 오토 세이브는 fire-and-forget 패턴 권장 — 실패해도 분석 흐름 중단 X.
 */

import type { AnalyzeRequest, AnalyzeResponse } from "./types";

const DB_NAME = "susemi";
const DB_VERSION = 1;
const STORE_ANALYSES = "analyses";

export type StoredAnalysis = {
  id: string;
  year: number;
  saved_at: string; // ISO timestamp
  label?: string;
  inputs: AnalyzeRequest;
  result: AnalyzeResponse;
};

// ---------- 환경 감지 ----------

export function isStorageAvailable(): boolean {
  return typeof window !== "undefined" && typeof window.indexedDB !== "undefined";
}

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

// ---------- 연결 (싱글톤) ----------

let _dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (!isStorageAvailable()) {
    return Promise.reject(new Error("IndexedDB unavailable"));
  }
  if (_dbPromise) return _dbPromise;

  _dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
    const req = window.indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_ANALYSES)) {
        const store = db.createObjectStore(STORE_ANALYSES, { keyPath: "id" });
        store.createIndex("year", "year", { unique: false });
        store.createIndex("saved_at", "saved_at", { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error ?? new Error("IndexedDB open failed"));
    req.onblocked = () =>
      reject(new Error("IndexedDB open blocked (다른 탭이 열려있는지 확인)"));
  });

  // 실패 캐싱 방지
  _dbPromise.catch(() => {
    _dbPromise = null;
  });
  return _dbPromise;
}

function withStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest<T>
): Promise<T> {
  return openDB().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE_ANALYSES, mode);
        const store = tx.objectStore(STORE_ANALYSES);
        const req = fn(store);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error ?? new Error("IDBRequest failed"));
      })
  );
}

// ---------- 공개 API ----------

export async function saveAnalysis(input: {
  year?: number;
  label?: string;
  inputs: AnalyzeRequest;
  result: AnalyzeResponse;
}): Promise<StoredAnalysis> {
  const item: StoredAnalysis = {
    id: uuid(),
    year: input.year ?? new Date().getFullYear(),
    saved_at: new Date().toISOString(),
    label: input.label,
    inputs: input.inputs,
    result: input.result,
  };
  await withStore<IDBValidKey>("readwrite", (s) => s.put(item));
  return item;
}

export async function listAnalyses(opts?: {
  year?: number;
  limit?: number;
}): Promise<StoredAnalysis[]> {
  try {
    const all = await withStore<StoredAnalysis[]>("readonly", (s) => s.getAll());
    let items = all ?? [];
    if (opts?.year != null) items = items.filter((i) => i.year === opts.year);
    items.sort((a, b) => (b.saved_at < a.saved_at ? -1 : 1));
    if (opts?.limit != null) items = items.slice(0, opts.limit);
    return items;
  } catch {
    return [];
  }
}

export async function loadAnalysis(id: string): Promise<StoredAnalysis | null> {
  try {
    const item = await withStore<StoredAnalysis | undefined>(
      "readonly",
      (s) => s.get(id)
    );
    return item ?? null;
  } catch {
    return null;
  }
}

export async function removeAnalysis(id: string): Promise<void> {
  try {
    await withStore<undefined>("readwrite", (s) => s.delete(id));
  } catch {
    /* ignore */
  }
}

export async function clearAnalyses(): Promise<void> {
  try {
    await withStore<undefined>("readwrite", (s) => s.clear());
  } catch {
    /* ignore */
  }
}
