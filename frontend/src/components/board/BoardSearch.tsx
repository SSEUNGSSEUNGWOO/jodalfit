"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";

type Mode = "company" | "keywords";

/** 개찰판 세계의 조회 폼 — 괘선 밑줄 입력 + 먹 버튼. compact는 판머리용. */
export function BoardSearch({
  variant = "full",
  defaultValue = "",
  initialMode = "company",
  className,
  examples,
  autoFocus = false,
  tone = "paper",
}: {
  variant?: "full" | "compact";
  defaultValue?: string;
  initialMode?: Mode;
  className?: string;
  examples?: { company?: string[]; keywords?: string[] };
  autoFocus?: boolean;
  /** full 변형의 배경 — band면 네이비 밴드 위 배색 */
  tone?: "paper" | "band";
}) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [value, setValue] = useState(defaultValue);
  const [loading, setLoading] = useState(false);

  const go = (q: string) => {
    if (!q || loading) return;
    setLoading(true);
    const param = mode === "company" ? "company" : "q";
    router.push(`/recommendations?${param}=${encodeURIComponent(q)}`);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    go(value.trim());
  };

  if (variant === "compact") {
    return (
      <form
        onSubmit={submit}
        className={cn("flex items-end gap-2", className)}
      >
        {/* compact 변형은 네이비 판머리 위에 놓인다 — 밴드 대비 색으로 */}
        <button
          type="button"
          onClick={() => setMode(mode === "company" ? "keywords" : "company")}
          className="shrink-0 h-8 px-2 text-[12px] font-bold text-gc-band-ink border border-gc-tint-line/60 rounded-[3px] hover:bg-white/10 transition-colors"
          aria-label="검색 모드 전환"
        >
          {mode === "company" ? "회사" : "키워드"}
        </button>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={mode === "company" ? "다른 회사 조회" : "키워드 조회"}
          aria-label={mode === "company" ? "회사 검색" : "키워드 검색"}
          className="w-[150px] sm:w-[190px] bg-transparent border-b border-gc-band-ink pb-1 text-[14px] font-semibold text-gc-band-hi placeholder:text-gc-band-ink placeholder:font-normal outline-none focus:border-white transition-colors [caret-color:var(--color-gc-band-hi)]"
        />
        <button
          type="submit"
          disabled={!value.trim() || loading}
          className="shrink-0 h-8 px-3 bg-gc-band-hi text-gc-band text-[12.5px] font-bold rounded-[3px] disabled:opacity-40 hover:bg-white transition-colors"
        >
          조회
        </button>
      </form>
    );
  }

  const isCompany = mode === "company";
  const band = tone === "band";
  return (
    <form onSubmit={submit} className={cn("w-full", className)}>
      <div
        className={cn(
          "inline-flex border rounded-[3px] overflow-hidden mb-5",
          band ? "border-gc-band-ink" : "border-gc-ink"
        )}
        role="tablist"
        aria-label="검색 모드"
      >
        {(
          [
            ["company", "회사 조회"],
            ["keywords", "키워드 조회"],
          ] as const
        ).map(([m, label]) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            onClick={() => setMode(m)}
            className={cn(
              "px-4 py-2 text-[13.5px] font-bold transition-colors",
              mode === m
                ? band
                  ? "bg-gc-band-hi text-gc-band"
                  : "bg-gc-band text-gc-band-hi"
                : band
                  ? "bg-transparent text-gc-band-ink hover:bg-white/10"
                  : "bg-transparent text-gc-ink-2 hover:bg-gc-sheet"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        className={cn(
          "flex items-end gap-3 border-b-2 pb-2",
          band ? "border-gc-band-ink" : "border-gc-ink"
        )}
      >
        <input
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={
            isCompany ? "회사명 또는 사업자번호 10자리" : "관심 영역 (예: 정보시스템 유지보수)"
          }
          aria-label={isCompany ? "회사명·사업자번호" : "관심 키워드"}
          className={cn(
            "flex-1 bg-transparent text-[19px] sm:text-[22px] font-bold placeholder:font-normal placeholder:text-[16px] sm:placeholder:text-[18px] outline-none min-w-0",
            band
              ? "text-gc-band-hi placeholder:text-gc-band-ink [caret-color:var(--color-gc-band-hi)]"
              : "text-gc-ink placeholder:text-gc-ink-3"
          )}
        />
        <button
          type="submit"
          disabled={!value.trim() || loading}
          className={cn(
            "shrink-0 h-11 px-5 text-[15px] font-bold rounded-[3px] disabled:opacity-40 transition-colors",
            band
              ? "bg-gc-band-hi text-gc-band hover:bg-white"
              : "bg-gc-band text-gc-band-hi hover:bg-gc-ink"
          )}
        >
          {loading ? "찾는 중…" : "찾기"}
        </button>
      </div>
      <p
        className={cn(
          "mt-2.5 text-[13px]",
          band ? "text-gc-band-ink" : "text-gc-ink-3"
        )}
      >
        {isCompany
          ? "등록업종·공급물품·수주 이력을 살펴보고 검토할 공고부터 보여드려요."
          : "같은 단어가 없어도 의미가 가까운 공고를 함께 찾습니다."}
      </p>

      {examples && (
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="text-[12.5px] font-bold text-gc-ink-2">
            {isCompany ? "예시 회사" : "예시 키워드"}
          </span>
          {(isCompany ? examples.company ?? [] : examples.keywords ?? []).map(
            (q) => (
              <button
                key={q}
                type="button"
                onClick={() => {
                  setValue(q);
                  go(q);
                }}
                className="px-3 py-1 text-[12.5px] font-semibold text-gc-ink-2 border border-gc-rule rounded-full bg-gc-sheet hover:border-gc-ink hover:text-gc-ink transition-colors"
              >
                {q}
              </button>
            )
          )}
        </div>
      )}
    </form>
  );
}
