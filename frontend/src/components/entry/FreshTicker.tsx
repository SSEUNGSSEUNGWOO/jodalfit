// frontend/src/components/entry/FreshTicker.tsx
// 입구 판의 등록 공고 — 세로 틱(시안 entry-simple, docs/design/README.md "세로 틱").
// 처음엔 최신 다섯 건, 4.5초마다 다음 공고가 위에서 한 행 들어오고 맨 아래 한 행이 나간다. 클립은 다섯 행
// 높이로 고정하고 안쪽만 translateY 로 밀어 레이아웃이 움직이지 않는다. 320ms cubic-bezier(.3,.7,.2,1).
// 멈춤: 판 hover · focus-within · 검색창에 글자 · 자동완성 열림 · 탭 숨김. 움직임 줄이기면 최신 다섯 건 고정.
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { EntryNotice } from "@/lib/entry";
import { cn } from "@/lib/utils";
import { dLeft } from "@/lib/format";

const ROWS = 5;
const EVERY_MS = 4500;
const SLIDE_MS = 320;
const nf = new Intl.NumberFormat("ko-KR");

function won(v: number | null): string {
  if (!v) return "—";
  return v >= 100_000_000 ? `${(v / 100_000_000).toFixed(1)}억` : `${nf.format(Math.round(v / 10_000))}만`;
}

// 사람이 검색 중이면 움직이는 목록이 시선을 뺏는다 — 입력에 글자가 있거나 자동완성이 열려 있으면 쉰다.
function searching(): boolean {
  const input = document.querySelector<HTMLInputElement>("[data-suggest] input");
  return !!input?.value.trim() || !!document.querySelector("#suggest-list");
}

export function FreshTicker({ items }: { items: EntryNotice[] }) {
  const [today] = useState(() => new Date());
  const [shown, setShown] = useState(() => items.slice(0, ROWS));
  const [next, setNext] = useState(ROWS % Math.max(1, items.length)); // 다음에 위로 들어올 공고
  const [phase, setPhase] = useState<"idle" | "enter" | "slide">("idle");
  const [rowH, setRowH] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const hold = useRef(false);
  const rolls = items.length > ROWS;

  useEffect(() => {
    if (!rolls || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const li = box.current?.querySelector("li");
    if (li) queueMicrotask(() => setRowH(li.getBoundingClientRect().height));
    let t = 0;
    const tick = () => {
      if (!hold.current && !document.hidden && !searching()) setPhase("enter");
      t = window.setTimeout(tick, EVERY_MS);
    };
    t = window.setTimeout(tick, EVERY_MS);
    return () => clearTimeout(t);
  }, [rolls]);

  // enter: 새 행을 위에 붙이고 -rowH 만큼 올려 둔 채 한 프레임 → slide: 0 으로 민다 → 끝나면 맨 아래를 버린다.
  useEffect(() => {
    if (phase === "enter") {
      const r = requestAnimationFrame(() => requestAnimationFrame(() => setPhase("slide")));
      return () => cancelAnimationFrame(r);
    }
    if (phase === "slide") {
      const d = window.setTimeout(() => {
        setShown((s) => [items[next], ...s].slice(0, ROWS));
        setNext((q) => (q + 1) % items.length);
        setPhase("idle");
      }, SLIDE_MS + 40);
      return () => clearTimeout(d);
    }
  }, [phase, items, next]);

  const rows = phase === "idle" ? shown : [items[next], ...shown];
  return (
    <div
      ref={box}
      onMouseEnter={() => (hold.current = true)}
      onMouseLeave={() => (hold.current = false)}
      onFocus={() => (hold.current = true)}
      onBlur={() => (hold.current = false)}
      className="mt-2 overflow-hidden"
      style={rowH ? { height: rowH * shown.length } : undefined}
    >
      <ul
        className={cn(phase === "slide" && "transition-transform duration-[320ms] [transition-timing-function:cubic-bezier(.3,.7,.2,1)]")}
        style={phase === "idle" ? undefined : { transform: `translateY(${phase === "slide" ? 0 : -rowH}px)` }}
      >
        {rows.map((r, i) => {
          const dl = dLeft(r.clse, today)?.days ?? null;
          return (
            <li
              key={r.no}
              className="grid grid-cols-[1fr_auto_auto] items-baseline gap-3.5 border-b border-rule py-[9px] max-sm:grid-cols-[1fr_auto]"
            >
              {/* 새로 들어온 행은 잠깐 진하게 — 색은 쓰지 않는다(주황은 선). 제목은 공고 페이지 링크(hover 주황 밑줄). */}
              <span className={cn("truncate transition-[font-weight] duration-[600ms]", phase !== "idle" && i === 0 && "font-[650]")}>
                <Link href={`/notices/${r.no}`} className="hover:border-b hover:border-orange">{r.nm}</Link>
                <span className="ml-2 text-[12.5px] text-ink-g">{r.instt || "—"}</span>
              </span>
              <span className="min-w-[76px] text-right text-[13px] text-ink-g">
                마감 <b className={cn("font-[650]", dl != null && dl <= 3 ? "text-orange-ink" : "text-ink")}>
                  {dl == null ? "—" : `D-${dl}`}
                </b>
              </span>
              <span className="num min-w-[62px] text-right text-[13px] text-ink-g max-sm:hidden">{won(r.amt)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
