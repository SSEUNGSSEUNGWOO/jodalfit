"use client";

import { Search, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";

export function SearchForm({
  variant = "primary",
  defaultValue = "",
  className,
  autoFocus = false,
}: {
  variant?: "primary" | "compact";
  defaultValue?: string;
  className?: string;
  autoFocus?: boolean;
}) {
  const router = useRouter();
  const [value, setValue] = useState(defaultValue);
  const [loading, setLoading] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (!q || loading) return;
    setLoading(true);
    router.push(`/recommendations?company=${encodeURIComponent(q)}`);
  };

  if (variant === "compact") {
    return (
      <form
        onSubmit={submit}
        className={cn(
          "flex items-center gap-2 rounded-tile border border-line bg-surface px-3 py-2 transition-colors focus-within:border-blue-500",
          className
        )}
      >
        <Search className="h-4 w-4 text-ink-soft" aria-hidden />
        <input
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="다른 회사 검색"
          className="flex-1 bg-transparent text-[14px] outline-none placeholder:text-ink-soft"
          aria-label="회사명"
        />
        <button
          type="submit"
          disabled={!value.trim() || loading}
          className="rounded-tile bg-navy px-3 py-1 text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          검색
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={submit} className={cn("group w-full", className)}>
      <div className="relative flex items-center rounded-card border border-line-strong bg-surface transition-shadow focus-within:border-navy focus-within:shadow-[0_8px_24px_-12px_rgba(18,53,91,0.18)]">
        <span className="pl-5 pr-3 text-ink-soft">
          <Search className="h-5 w-5" aria-hidden />
        </span>
        <input
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="예: 주식회사 제이오달소프트"
          aria-label="회사명을 입력하세요"
          className="flex-1 bg-transparent py-[18px] text-[16px] outline-none placeholder:text-ink-soft sm:text-[17px]"
        />
        <button
          type="submit"
          disabled={!value.trim() || loading}
          className="my-2 mr-2 flex items-center gap-2 rounded-tile bg-navy px-5 py-3 text-[14px] font-semibold text-white transition-all hover:bg-navy-700 disabled:cursor-not-allowed disabled:opacity-50 sm:px-6"
        >
          {loading ? "분석 중..." : "추천 공고 보기"}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
      <p className="mt-3 px-2 text-[13px] text-ink-muted">
        회원가입 없이 먼저 확인.{" "}
        <span className="text-ink-soft">검색 기록은 저장되지 않습니다.</span>
      </p>
    </form>
  );
}
