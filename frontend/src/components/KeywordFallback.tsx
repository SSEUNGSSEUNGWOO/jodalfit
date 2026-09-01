"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const SUGGESTED = [
  "AI 시스템 구축",
  "정보시스템 유지보수",
  "교육청 SI",
  "클라우드 전환",
  "데이터 분석 플랫폼",
  "보안 컨설팅",
  "홈페이지 개편",
  "민원시스템 고도화",
];

export function KeywordFallback({
  title = "어떤 분야의 공고를 찾으시나요?",
  subtitle,
  defaultQuery = "",
  className,
}: {
  title?: string;
  subtitle?: string;
  defaultQuery?: string;
  className?: string;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [value, setValue] = useState(defaultQuery);
  const [loading, setLoading] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    if (!q || loading) return;
    setLoading(true);
    const newParams = new URLSearchParams();
    newParams.set("q", q);
    newParams.set("mode", "keywords");
    // 회사 컨텍스트 살리고 싶으면 company 파라미터도 유지
    const company = params.get("company");
    if (company) newParams.set("company", company);
    router.push(`/recommendations?${newParams.toString()}`);
  };

  const addKeyword = (kw: string) => {
    setValue((cur) => {
      const cleaned = cur.trim();
      if (!cleaned) return kw;
      if (cleaned.toLowerCase().includes(kw.toLowerCase())) return cleaned;
      return `${cleaned}, ${kw}`;
    });
  };

  return (
    <Card className={cn("border-primary/15 bg-primary/5", className)}>
      <CardContent className="px-6 py-7 sm:px-8 sm:py-8">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-4 w-4 text-primary" aria-hidden />
          <span className="text-[12.5px] font-bold text-primary">관심 분야로 공고 찾기</span>
        </div>

        <h3 className="text-[22px] sm:text-[24px] font-extrabold tracking-tight text-foreground">
          {title}
        </h3>
        {subtitle ? (
          <p className="mt-2 text-[14.5px] leading-relaxed text-muted-foreground max-w-[52ch]">
            {subtitle}
          </p>
        ) : (
          <p className="mt-2 text-[14.5px] leading-relaxed text-muted-foreground max-w-[52ch]">
            과거 낙찰 이력이 부족해서 분석이 어려워요. 대신{" "}
            <span className="text-foreground font-semibold">관심 분야를 직접 입력</span>해 주시면
            그 키워드로 가장 잘 맞는 공고 5개를 찾아드려요.
          </p>
        )}

        <form onSubmit={submit} className="mt-6 space-y-3">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="예) AI 콜센터 구축, 교육청 시스템 유지보수, 클라우드 마이그레이션"
            rows={3}
            className={cn(
              "w-full rounded-xl bg-background border border-input px-4 py-3",
              "text-[15px] font-medium text-foreground",
              "placeholder:font-normal placeholder:text-muted-foreground",
              "outline-none transition-all resize-none",
              "focus:ring-2 focus:ring-primary focus:border-primary"
            )}
          />

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[12px] font-semibold text-muted-foreground mr-1">
              예시 클릭
            </span>
            {SUGGESTED.map((kw) => (
              <button
                key={kw}
                type="button"
                onClick={() => addKeyword(kw)}
                className={cn(
                  "px-2.5 py-1 rounded-full text-[12.5px] font-semibold transition-colors",
                  "bg-background border border-input text-foreground/80",
                  "hover:bg-primary hover:text-primary-foreground hover:border-primary"
                )}
              >
                + {kw}
              </button>
            ))}
          </div>

          <Button
            type="submit"
            size="lg"
            disabled={!value.trim() || loading}
            className="h-12 px-5 gap-1.5 text-[15px]"
          >
            {loading ? "찾는 중…" : "이 키워드로 찾기"}
            {!loading && <ArrowRight className="h-4 w-4" aria-hidden />}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
