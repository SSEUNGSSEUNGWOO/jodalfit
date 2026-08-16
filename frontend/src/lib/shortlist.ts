"use client";

import { useCallback, useSyncExternalStore } from "react";

const KEY = "jf_shortlist_v1";

export interface ShortlistItem {
  k: string; // `${bid_ntce_no}-${bid_ntce_ord}`
  bid_ntce_no: string;
  bid_ntce_ord: string;
  bid_ntce_nm: string;
  bid_clse_date: string | null;
  saved_at: string;
}

const EMPTY: ShortlistItem[] = [];
let cache: ShortlistItem[] | null = null;
const listeners = new Set<() => void>();

function read(): ShortlistItem[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : EMPTY;
  } catch {
    return EMPTY;
  }
}

function write(items: ShortlistItem[]) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    // 저장 실패(프라이빗 모드 등)는 무시 — 세션 내 상태로만 동작
  }
}

function getSnapshot(): ShortlistItem[] {
  if (cache === null) cache = read();
  return cache;
}

function getServerSnapshot(): ShortlistItem[] {
  return EMPTY;
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function emit() {
  for (const l of listeners) l();
}

/** 검토 인장(저장) 목록 — localStorage 기반, 회원가입 없이 동작 */
export function useShortlist() {
  const items = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const has = useCallback(
    (k: string) => items.some((it) => it.k === k),
    [items]
  );

  const toggle = useCallback((item: Omit<ShortlistItem, "saved_at">) => {
    const cur = getSnapshot();
    const exists = cur.some((it) => it.k === item.k);
    cache = exists
      ? cur.filter((it) => it.k !== item.k)
      : [...cur, { ...item, saved_at: new Date().toISOString() }];
    write(cache);
    emit();
  }, []);

  return { items, has, toggle, count: items.length };
}
