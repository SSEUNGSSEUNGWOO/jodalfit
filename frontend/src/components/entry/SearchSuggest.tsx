// frontend/src/components/entry/SearchSuggest.tsx
// 입구 검색창 — 검색 기준(회사 / 키워드) 선택 + 자동완성. 시안 entry-v2 의 D 안(gen_entry_v2.py)을 옮긴다.
//
// 검색 기준을 먼저 고른다(2026-10-24 승우님) — 한 칸이 회사명도 키워드도 받으면 처음 온 사람은 무엇으로 찾는지 모른다.
// 회사: 두 글자부터 회사 목록이 아래로 자란다 · ↑↓ 로 옮긴다 · Enter·클릭으로 고른다 · Esc 로 닫는다.
//       일치하는 회사가 없으면 그 자리에 '키워드로 찾기' 한 줄 — 입력의 절반 이상이 회사명이 아니다(업종·품목·브랜드).
// 키워드: 목록 없이 Enter 로 바로 찾는다.
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { track } from "@/lib/analytics";
import type { CompanySuggestion } from "@/app/api/companies/suggest/route";
import { cn } from "@/lib/utils";

const MIN = 2;
const DEBOUNCE_MS = 140;

export type SearchMode = "company" | "keywords";
type Mode = SearchMode;
const MODES: { mode: Mode; label: string; placeholder: string }[] = [
  { mode: "company", label: "회사로 찾기", placeholder: "회사명 또는 사업자등록번호" },
  { mode: "keywords", label: "키워드로 찾기", placeholder: "업종 또는 품목 — 예: 하수처리시설 관리대행" },
];

export function SearchSuggest({ autoFocus = false, initialMode = "company", onModeChange, lock, placeholder, compact = false, onPick, submitLabel = "찾기" }: {
  autoFocus?: boolean; initialMode?: Mode; onModeChange?: (m: Mode) => void; // 입구 제목·안내 줄이 기준을 따라 바뀐다(EntrySearch)
  lock?: Mode;          // 기준을 고정하고 탭을 숨긴다 — 회사 페이지의 다리(OwnCompanyBridge)처럼 뜻이 이미 정해진 자리(2026-10-27)
  placeholder?: string; // 자리글을 그 자리의 말로
  compact?: boolean;    // 입구보다 한 단계 작게
  onPick?: (nm: string) => void; // 회사 모드에서 고른 이름을 결과 페이지로 보내지 않고 넘긴다 — 회사 저장 폼(SaveCompanyForm, 2026-10-28). 키워드 폴백 줄은 없다.
  submitLabel?: string; // 제출 버튼 글자(기본 "찾기") — 저장 폼은 "저장"
}) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>(lock ?? initialMode);
  const [q, setQ] = useState("");
  const [cos, setCos] = useState<CompanySuggestion[]>([]);
  const [suggestQuery, setSuggestQuery] = useState("");
  const [closed, setClosed] = useState(false); // 사용자가 Esc·바깥 클릭으로 닫았는가 — 열림은 계산으로 낸다
  const [act, setAct] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  // 입력이 멈추면 한 번만 친다. 늦게 온 응답이 최신 입력을 덮어쓰지 않게 live 로 끊는다.
  // 효과 안에서 직접 상태를 바꾸지 않는다(react-hooks/set-state-in-effect) — 비동기 콜백에서만.
  useEffect(() => {
    const v = q.trim();
    if (mode !== "company" || v.length < MIN) return;
    let live = true;
    const t = setTimeout(() => {
      fetch(`/api/companies/suggest?q=${encodeURIComponent(v)}`)
        .then((r) => (r.ok ? r.json() : []))
        .then((rows: CompanySuggestion[]) => {
          if (!live) return;
          setCos(rows);
          setSuggestQuery(v);
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
  }, [q, mode]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setClosed(true);
    };
    addEventListener("mousedown", onDown);
    return () => removeEventListener("mousedown", onDown);
  }, []);

  // 회사 모드 목록: 응답이 현재 입력의 것일 때만. 응답이 왔는데 0곳이면 '키워드로 찾기' 한 줄(co: null).
  const answered = mode === "company" && q.trim().length >= MIN && suggestQuery === q.trim();
  const rows: { co: CompanySuggestion | null }[] = !answered ? [] : cos.length ? cos.map((c) => ({ co: c })) : [{ co: null }];

  function submit(m: Mode, v: string, from: string) {
    setClosed(true);
    track("search_submit", { mode: m, length: v.length, from });
    router.push(m === "company" ? `/recommendations?company=${encodeURIComponent(v)}` : `/recommendations?q=${encodeURIComponent(v)}`);
  }

  function go(i: number | null) {
    const v = q.trim();
    if (!v) return;
    const r = i == null ? undefined : rows[i];
    if (onPick) { setClosed(true); return onPick(r?.co ? r.co.nm : v); }
    if (r?.co) return submit("company", r.co.nm, "suggest");
    if (r && !r.co) return submit("keywords", v, "suggest_keyword");
    // 목록 없이 제출 — 고른 기준 그대로. 회사 모드에서 못 찾으면 결과 페이지가 키워드로 넘긴다.
    submit(mode, v, "submit");
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;
    if (!show) return; // Enter 는 form 제출이 받는다
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

  function pick(m: Mode) {
    setMode(m);
    onModeChange?.(m);
    setClosed(false);
    setAct(0);
    input.current?.focus();
  }

  const show = !closed && rows.length > 0;
  const cur = MODES.find((m) => m.mode === mode)!;
  return (
    <div ref={box} className="relative max-w-[760px]" data-suggest data-mode={mode}>
      {!lock && <div role="radiogroup" aria-label="검색 기준" className="mb-2.5 flex gap-5 text-[14px]">
        {MODES.map((m) => (
          <button
            key={m.mode}
            type="button"
            role="radio"
            aria-checked={mode === m.mode}
            data-search-mode={m.mode}
            onClick={() => pick(m.mode)}
            className={cn(
              "cursor-pointer border-b-2 pb-1 transition-colors",
              mode === m.mode ? "border-ink font-[650] text-ink" : "border-transparent text-ink-mute hover:text-ink-g",
            )}
          >
            {m.label}
          </button>
        ))}
      </div>}
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          go(show ? act : null);
        }}
        className="flex items-stretch rounded-[6px] border-2 border-orange bg-panel transition-shadow duration-150 focus-within:shadow-[0_0_0_4px_var(--color-orange-ring)]"
      >
        <input
          ref={input}
          value={q}
          onChange={(e) => {
            const v = e.target.value;
            setQ(v);
            setClosed(false);
            setAct(0);
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
          aria-activedescendant={show ? `suggest-option-${act}` : undefined}
          placeholder={placeholder ?? cur.placeholder}
          aria-label={placeholder ?? cur.placeholder}
          className={cn("min-w-0 flex-1 bg-transparent font-medium tracking-[-0.02em] text-ink outline-none placeholder:font-[450] placeholder:text-ink-mute",
            compact ? "px-3.5 py-2.5 text-[16px] placeholder:text-[14.5px]" : "px-[18px] py-3.5 text-[20px] max-sm:px-3.5 max-sm:py-3 max-sm:text-[17px] max-sm:placeholder:text-[15px]")}
        />
        <button type="submit" className={cn("cursor-pointer border-l border-rule bg-panel font-[650] text-ink", compact ? "px-4 text-[14px]" : "px-5 text-[15px] max-sm:px-3.5")}>
          <span className="border-b-2 border-orange pb-px">{submitLabel}</span>
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
              id={`suggest-option-${i}`}
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
                  <span className="truncate text-ink-g">일치하는 회사 없음</span>
                  {!onPick && <span className="ml-auto shrink-0 text-[12.5px] text-ink">&quot;{q.trim()}&quot; 키워드로 찾기</span>}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
