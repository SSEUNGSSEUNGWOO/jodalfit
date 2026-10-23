// frontend/src/components/SearchBox.tsx
// 주황 테두리 검색창 하나 — 회사명·사업자번호·업종/품목. 제출은 /recommendations 로 이동(회사명/사업자번호면 company, 그 외 keywords).
// 사업자번호(숫자 10자리, 하이픈 허용)·회사 접미(주식회사·(주)·㈜·유한회사·(유))가 보이면 회사 모드, 아니면 키워드 모드.
"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/utils";

const CO_HINT = /(주식회사|\(주\)|㈜|유한회사|\(유\)|합자회사|법인)/;

export function modeOf(q: string): "company" | "keywords" {
  const digits = q.replace(/\D/g, "");
  if (/^[\d-]+$/.test(q.trim()) && digits.length === 10) return "company";
  return CO_HINT.test(q) ? "company" : "keywords";
}

export function SearchBox({ defaultValue = "", autoFocus = false, className, onSubmitted }: { defaultValue?: string; autoFocus?: boolean; className?: string; onSubmitted?: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState(defaultValue);
  function submit(e: FormEvent) {
    e.preventDefault();
    const v = q.trim();
    if (!v) return;
    const mode = modeOf(v);
    track("search_submit", { mode, length: v.length });
    router.push(mode === "company" ? `/recommendations?company=${encodeURIComponent(v)}` : `/recommendations?q=${encodeURIComponent(v)}`);
    onSubmitted?.();
  }
  return (
    <form onSubmit={submit} role="search" data-searchbox
      className={cn("flex max-w-[720px] items-stretch rounded-[6px] border-2 border-orange bg-panel transition-shadow duration-150 focus-within:shadow-[0_0_0_4px_rgba(249,115,22,.18)]", className)}>
      <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus={autoFocus} autoComplete="off" spellCheck={false}
        placeholder="회사명 · 사업자등록번호 · 업종 또는 품목" aria-label="회사명, 사업자등록번호, 업종 또는 품목"
        className="min-w-0 flex-1 bg-transparent px-[18px] py-3.5 text-[20px] font-medium tracking-[-0.02em] text-ink outline-none placeholder:font-[450] placeholder:text-ink-mute max-sm:px-3.5 max-sm:py-3 max-sm:text-[17px]" />
      <button type="submit" className="cursor-pointer border-l border-rule bg-panel px-5 text-[15px] font-[650] text-ink max-sm:px-3.5">
        <span className="border-b-2 border-orange pb-px">찾기</span>
      </button>
    </form>
  );
}
