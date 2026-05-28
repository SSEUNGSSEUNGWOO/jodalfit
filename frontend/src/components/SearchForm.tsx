"use client";

import { ArrowRight, Building2, Search, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Mode = "company" | "keywords";

interface CommonProps {
  variant?: "primary" | "compact";
  defaultValue?: string;
  /** primary 변형에서 초기 활성 탭 */
  initialMode?: Mode;
  className?: string;
  autoFocus?: boolean;
  /** primary 변형에서 검색창 아래 노출할 예시 칩 — 활성 모드에 맞춰 노출됨 */
  examples?: { company?: string[]; keywords?: string[] };
}

export function SearchForm({
  variant = "primary",
  defaultValue = "",
  initialMode = "company",
  className,
  autoFocus = false,
  examples,
}: CommonProps) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [value, setValue] = useState(defaultValue);
  const [loading, setLoading] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (!q || loading) return;
    setLoading(true);
    if (mode === "company") {
      router.push(`/recommendations?company=${encodeURIComponent(q)}`);
    } else {
      router.push(`/recommendations?q=${encodeURIComponent(q)}`);
    }
  };

  if (variant === "compact") {
    // 컴팩트(결과 페이지 헤더): 작은 모드 토글 + 단일 입력란
    const compactPlaceholder = mode === "company" ? "회사명 / 사업자번호" : "관심 키워드";
    return (
      <form
        onSubmit={submit}
        className={cn(
          "flex items-center gap-1.5 rounded-lg bg-muted/60 pl-1 pr-1 h-11 transition-colors focus-within:bg-muted focus-within:ring-2 focus-within:ring-primary/30",
          className
        )}
      >
        <button
          type="button"
          onClick={() => setMode(mode === "company" ? "keywords" : "company")}
          className="flex items-center gap-1 h-9 px-2 rounded-md text-[11px] font-bold text-primary hover:bg-primary/10 transition-colors shrink-0"
          title="검색 모드 전환"
          aria-label="검색 모드 전환"
        >
          {mode === "company" ? (
            <>
              <Building2 className="h-3.5 w-3.5" aria-hidden />
              회사
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5" aria-hidden />
              키워드
            </>
          )}
        </button>
        <span className="text-muted-foreground/40">|</span>
        <input
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={compactPlaceholder}
          className="flex-1 bg-transparent text-sm font-medium outline-none placeholder:text-muted-foreground min-w-0"
          aria-label={mode === "company" ? "회사 검색" : "키워드 검색"}
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

  const isCompany = mode === "company";
  const placeholder = isCompany
    ? "회사명 또는 사업자번호 입력 (예: 삼성SDS)"
    : "관심 영역 입력 (예: 교육 IT 유지보수)";
  const helper = isCompany
    ? "사업자번호 10자리로도 검색할 수 있습니다."
    : "같은 단어가 없어도 의미가 가까운 공고를 함께 찾습니다.";

  return (
    <form onSubmit={submit} className={cn("w-full", className)}>
      {/* 탭 */}
      <div className="flex items-center gap-1.5 mb-2.5">
        <TabButton active={isCompany} onClick={() => setMode("company")}>
          <Building2 className="h-3.5 w-3.5" aria-hidden />
          회사 검색
        </TabButton>
        <TabButton active={!isCompany} onClick={() => setMode("keywords")}>
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          키워드 검색
        </TabButton>
        {!isCompany && (
          <span className="ml-1 inline-flex items-center gap-1 text-[11px] font-bold text-primary uppercase tracking-wider">
            <span className="inline-block size-1 rounded-full bg-primary" />
            의미 매칭
          </span>
        )}
      </div>

      <div className="relative">
        <Search
          className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground pointer-events-none"
          aria-hidden
        />
        <input
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          aria-label={isCompany ? "회사명·사업자번호" : "관심 키워드"}
          className={cn(
            "w-full h-[68px] pl-14 pr-[150px] rounded-2xl bg-muted",
            "border-2 border-foreground",
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
      <p className="mt-3 ml-1 text-sm text-muted-foreground">{helper}</p>

      {examples && (
        <ExampleChips
          items={isCompany ? examples.company ?? [] : examples.keywords ?? []}
          label={isCompany ? "예시 회사" : "예시 키워드"}
          onPick={(q) => {
            setValue(q);
            // 자동 제출 — 사용자가 한 번 클릭으로 결과 페이지로
            setLoading(true);
            if (isCompany) {
              router.push(`/recommendations?company=${encodeURIComponent(q)}`);
            } else {
              router.push(`/recommendations?q=${encodeURIComponent(q)}`);
            }
          }}
        />
      )}
    </form>
  );
}

function ExampleChips({
  items,
  label,
  onPick,
}: {
  items: string[];
  label: string;
  onPick: (q: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-4 flex flex-wrap items-center gap-1.5">
      <span className="text-[13px] text-muted-foreground mr-1">{label}</span>
      {items.map((q) => (
        <button
          key={q}
          type="button"
          onClick={() => onPick(q)}
          className="chip hover:bg-bg-soft-2 transition-colors"
        >
          {q}
        </button>
      ))}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-[13px] font-bold transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}
