import Link from "next/link";
import { cn } from "@/lib/utils";

/**
 * Brand identity — "판의 행" (2026-08 청색 장부 리브랜딩)
 * 괘선 목록 속에서 우리 회사 행만 채워지고 인장(인주 점)이 찍히는 순간.
 * 괘선·채움 행은 currentColor, 인주 점만 고정 색 — 어느 잉크 위에서도 성립.
 */
export function JodalfitSymbol({
  className,
  dotColor = "var(--color-gc-injuk, #B23A2A)",
}: {
  className?: string;
  dotColor?: string;
}) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      role="img"
      aria-label="조달핏"
    >
      <line
        x1="12"
        y1="22"
        x2="88"
        y2="22"
        stroke="currentColor"
        strokeWidth="10"
        strokeLinecap="round"
      />
      <rect x="12" y="40" width="61" height="20" rx="5" fill="currentColor" />
      <circle cx="84" cy="50" r="9" fill={dotColor} />
      <line
        x1="12"
        y1="78"
        x2="88"
        y2="78"
        stroke="currentColor"
        strokeWidth="10"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Brand({
  className,
  size = "md",
  href = "/",
  variant = "wordmark",
}: {
  className?: string;
  size?: "sm" | "md" | "lg";
  href?: string | null;
  variant?: "wordmark" | "symbol";
}) {
  const symbolSize = { sm: "h-5 w-5", md: "h-6 w-6", lg: "h-8 w-8" }[size];
  const textSize = { sm: "text-[17px]", md: "text-[20px]", lg: "text-[26px]" }[
    size
  ];

  const content = (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <JodalfitSymbol className={cn("text-primary shrink-0", symbolSize)} />
      {variant === "wordmark" && (
        <span
          className={cn(
            "font-gc-serif font-black tracking-[-0.02em] text-ink leading-none",
            textSize
          )}
        >
          조달핏
        </span>
      )}
    </span>
  );

  if (!href) return content;
  return (
    <Link
      href={href}
      className="inline-flex items-center hover:opacity-80 transition-opacity"
      aria-label="조달핏 홈"
    >
      {content}
    </Link>
  );
}
