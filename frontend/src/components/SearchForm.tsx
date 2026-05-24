"use client";

import { ArrowRight, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
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
          "flex items-center gap-2 rounded-lg bg-muted/60 px-3 h-11 transition-colors focus-within:bg-muted focus-within:ring-2 focus-within:ring-primary/30",
          className
        )}
      >
        <Search className="h-4 w-4 text-muted-foreground" aria-hidden />
        <input
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="다른 회사 검색"
          className="flex-1 bg-transparent text-sm font-medium outline-none placeholder:text-muted-foreground"
          aria-label="회사명"
        />
        <Button
          type="submit"
          size="sm"
          disabled={!value.trim() || loading}
          variant="default"
        >
          검색
        </Button>
      </form>
    );
  }

  return (
    <form onSubmit={submit} className={cn("w-full", className)}>
      <div className="relative">
        <Search
          className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground pointer-events-none"
          aria-hidden
        />
        <input
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="회사명을 입력해보세요"
          aria-label="회사명을 입력하세요"
          className={cn(
            "w-full h-[68px] pl-14 pr-[150px] rounded-2xl bg-muted",
            "text-[18px] font-semibold text-foreground",
            "placeholder:font-normal placeholder:text-muted-foreground",
            "outline-none transition-all",
            "focus:bg-background focus:ring-2 focus:ring-primary"
          )}
        />
        <Button
          type="submit"
          size="lg"
          disabled={!value.trim() || loading}
          className="absolute right-2 top-1/2 -translate-y-1/2 h-[52px] px-5 text-[15px] gap-1.5"
        >
          {loading ? "분석 중..." : "추천 받기"}
          {!loading && <ArrowRight className="h-4 w-4" aria-hidden />}
        </Button>
      </div>
      <p className="mt-3 ml-1 text-sm text-muted-foreground">
        회원가입 없이 바로 확인할 수 있어요.
      </p>
    </form>
  );
}
