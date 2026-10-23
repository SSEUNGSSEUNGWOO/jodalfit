// frontend/src/components/entry/SearchSuggest.tsx
// 입구 검색창 — SearchBox 에 자동완성을 더한 것. 시안 entry-v2 의 D 안(gen_entry_v2.py)을 옮긴다.
//
// 조작: 두 글자부터 아래로 자란다 · ↑↓ 로 옮긴다 · Enter·클릭으로 고른다 · Esc 로 닫는다.
// 목록 끝에는 항상 '그대로 찾기' 한 줄을 둔다 — 입력의 절반 이상이 회사명이 아니다(업종·품목·브랜드).
// 회사를 고르면 회사 모드로, 그 줄을 고르면 키워드 모드로 간다.
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { track } from "@/lib/analytics";
import { modeOf } from "@/components/SearchBox";
import type { CompanySuggestion } from "@/app/api/companies/suggest/route";
import { cn } from "@/lib/utils";

const MIN = 2;
const DEBOUNCE_MS = 140;

export function SearchSuggest({ autoFocus = false }: { autoFocus?: boolean }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [cos, setCos] = useState<CompanySuggestion[]>([]);
  const [closed, setClosed] = useState(false); // 사용자가 Esc·바깥 클릭으로 닫았는가 — 열림은 계산으로 낸다
  const [act, setAct] = useState(0);
  const box = useRef<HTMLDivElement>(null);

  // 입력이 멈추면 한 번만 친다. 늦게 온 응답이 최신 입력을 덮어쓰지 않게 live 로 끊는다.
  // 효과 안에서 직접 상태를 바꾸지 않는다(react-hooks/set-state-in-effect) — 비동기 콜백에서만.
  useEffect(() => {
    const v = q.trim();
    if (v.length < MIN) return;
    let live = true;
    const t = setTimeout(() => {
      fetch(`/api/companies/suggest?q=${encodeURIComponent(v)}`)
        .then((r) => (r.ok ? r.json() : []))
        .then((rows: CompanySuggestion[]) => {
          if (!live) return;
          setCos(rows);
          setAct(0);
        })
        .catch(() => {
          // 자동완성이 죽어도 검색 자체는 되어야 한다 — 목록만 비우고 조용히 넘어간다.
          if (live) setCos([]);
        });
    }, DEBOUNCE_MS);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setClosed(true);
    };
    addEventListener("mousedown", onDown);
    return () => removeEventListener("mousedown", onDown);
  }, []);

  // 마지막 줄은 '그대로 찾기'(키워드). 목록이 비어도 이 줄은 남는다.
  const rows = q.trim().length >= MIN ? [...cos.map((c) => ({ co: c })), { co: null }] : [];

  function go(i: number) {
    const r = rows[i];
    const v = q.trim();
    if (!r || !v) return;
    setClosed(true);
    if (r.co) {
      track("search_submit", { mode: "company", length: r.co.nm.length, from: "suggest" });
      router.push(`/recommendations?company=${encodeURIComponent(r.co.nm)}`);
      return;
    }
    const mode = modeOf(v);
    track("search_submit", { mode, length: v.length, from: "suggest_keyword" });
    router.push(mode === "company" ? `/recommendations?company=${encodeURIComponent(v)}` : `/recommendations?q=${encodeURIComponent(v)}`);
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!show) {
      if (e.key === "Enter" && q.trim()) {
        e.preventDefault();
        go(rows.length - 1); // 목록이 닫혀 있으면 입력 그대로
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setAct((a) => (a + 1) % rows.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setAct((a) => (a - 1 + rows.length) % rows.length);
    } else if (e.key === "Escape") {
      setClosed(true);
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(act);
    }
  }

  const show = !closed && rows.length > 0;
  return (
    <div ref={box} className="relative max-w-[760px]" data-suggest>
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          go(show ? act : rows.length - 1);
        }}
        className="flex items-stretch rounded-[6px] border-2 border-orange bg-panel transition-shadow duration-150 focus-within:shadow-[0_0_0_4px_var(--color-orange-ring)]"
      >
        <input
          value={q}
          onChange={(e) => {
            const v = e.target.value;
            setQ(v);
            setClosed(false);
            if (v.trim().length < MIN) setCos([]); // 짧아지면 이전 후보가 남지 않게
          }}
          onKeyDown={onKey}
          onFocus={() => setClosed(false)}
          autoFocus={autoFocus}
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-expanded={show}
          aria-controls="suggest-list"
          aria-autocomplete="list"
          placeholder="회사명 · 사업자등록번호 · 업종 또는 품목"
          aria-label="회사명, 사업자등록번호, 업종 또는 품목"
          className="min-w-0 flex-1 bg-transparent px-[18px] py-3.5 text-[20px] font-medium tracking-[-0.02em] text-ink outline-none placeholder:font-[450] placeholder:text-ink-mute max-sm:px-3.5 max-sm:py-3 max-sm:text-[17px]"
        />
        <button type="submit" className="cursor-pointer border-l border-rule bg-panel px-5 text-[15px] font-[650] text-ink max-sm:px-3.5">
          <span className="border-b-2 border-orange pb-px">찾기</span>
        </button>
      </form>

      {show && (
        <div
          id="suggest-list"
          role="listbox"
          className="absolute inset-x-0 top-[calc(100%+4px)] z-10 overflow-hidden rounded-[3px] border border-field bg-panel shadow-[0_6px_20px_rgba(20,20,20,.07)]"
        >
          {rows.map((r, i) => (
            <div
              key={r.co ? r.co.nm + r.co.rgn : "__kw"}
              role="option"
              aria-selected={i === act}
              onMouseEnter={() => setAct(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                go(i);
              }}
              className={cn(
                "flex cursor-pointer items-baseline gap-2.5 px-4 py-2.5 text-[14.5px]",
                i > 0 && "border-t border-hair",
                i === act && "bg-rule-2",
              )}
            >
              {r.co ? (
                <>
                  <span className="truncate font-semibold">{r.co.nm}</span>
                  <span className="truncate text-[12.5px] text-ink-mute">{r.co.rgn || "지역 미상"}</span>
                  <span className="ml-auto shrink-0 text-[12.5px] text-ink-mute">등록업종 {r.co.industries}</span>
                </>
              ) : (
                <>
                  <span className="truncate text-ink-g">&quot;{q.trim()}&quot; 그대로 찾기</span>
                  <span className="ml-auto shrink-0 text-[12.5px] text-ink-mute">업종·품목으로</span>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
