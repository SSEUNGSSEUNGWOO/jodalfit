// frontend/src/components/entry/RecentChips.tsx
// 입구의 최근 조회 칩 — 전에 본 회사를 다시 치지 않게.
//
// 브라우저에만 남긴다(localStorage). 로그인 없이 쓰는 제품이고, 서버에 두면 저장한 회사(03)와
// 뜻이 겹친다 — 저장은 "다시 볼 것", 최근 조회는 "방금 본 것"이다.
// 서버 렌더에는 없는 값이라 마운트 뒤에 읽는다(하이드레이션 불일치 방지).
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const KEY = "jf.recent.companies";
const MAX = 5;

export type RecentCompany = { nm: string; rgn?: string };

/** 결과 페이지가 회사를 확정했을 때 부른다. 같은 회사는 앞으로 끌어올린다. */
export function rememberCompany(co: RecentCompany) {
  if (typeof localStorage === "undefined" || !co.nm) return;
  try {
    const prev = readRecent().filter((c) => c.nm !== co.nm);
    localStorage.setItem(KEY, JSON.stringify([co, ...prev].slice(0, MAX)));
  } catch {
    // 사파리 비공개 모드 등 — 기억 못 해도 제품은 돌아간다
  }
}

function readRecent(): RecentCompany[] {
  try {
    const raw = localStorage.getItem(KEY);
    const arr = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(arr) ? arr.filter((c): c is RecentCompany => !!c && typeof (c as RecentCompany).nm === "string") : [];
  } catch {
    return [];
  }
}

export function RecentChips() {
  const [items, setItems] = useState<RecentCompany[]>([]);
  useEffect(() => {
    // 효과 안에서 바로 setState 하지 않는다(react-hooks/set-state-in-effect).
    queueMicrotask(() => setItems(readRecent()));
  }, []);
  if (!items.length) return null;
  return (
    <div className="mx-auto mt-3.5 flex max-w-[760px] flex-wrap items-center gap-x-2 gap-y-1.5">
      <span className="text-[12.5px] text-ink-mute">최근 조회</span>
      {items.map((c) => (
        <Link
          key={c.nm}
          href={`/recommendations?company=${encodeURIComponent(c.nm)}`}
          className="rounded-full border border-field px-2.5 py-1 text-[13px] text-ink-g transition-colors hover:border-orange hover:text-ink"
        >
          {c.nm}
        </Link>
      ))}
      <button
        type="button"
        onClick={() => {
          try {
            localStorage.removeItem(KEY);
          } catch {
            /* 지우지 못해도 화면은 비운다 */
          }
          setItems([]);
        }}
        className="cursor-pointer text-[12.5px] text-ink-mute underline-offset-2 hover:underline"
      >
        지우기
      </button>
    </div>
  );
}
