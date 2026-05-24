import Link from "next/link";
import { cn } from "@/lib/utils";

/**
 * Brand identity — currently using concept 10 Halves.
 * 두 컨셉(Registration · Halves) 모두 export. Brand 컴포넌트에서 concept prop으로 전환 가능.
 *
 * Halves: 채워진 삼각형(회사 이력) + 윤곽 삼각형(공고)이 대각선을 따라 맞물려 사각형
 * Registration: 인쇄 등록 마크(crop marks) — 4 모서리 + 중앙 도트
 */

// ───── HALVES (concept 10) ────────────────────────────────────
export function JodalfitHalvesSymbol({
  className,
  strokeWidth = 9,
}: {
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={className}
      role="img"
      aria-label="jodalfit"
    >
      <polygon points="35,35 165,35 35,165" fill="currentColor" />
      <polygon
        points="165,35 165,165 35,165"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="miter"
      />
    </svg>
  );
}

export function JodalfitHalvesWordmark({
  className,
  strokeWidth = 9,
}: {
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      viewBox="0 0 720 200"
      className={className}
      role="img"
      aria-label="jodalfit"
    >
      <polygon points="35,35 165,35 35,165" fill="currentColor" />
      <polygon
        points="165,35 165,165 35,165"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="miter"
      />
      <text
        x="220"
        y="138"
        fill="currentColor"
        fontFamily="Manrope, 'Pretendard Variable', Pretendard, system-ui, -apple-system, 'Segoe UI', sans-serif"
        fontWeight="700"
        fontSize="120"
        letterSpacing="-5"
      >
        jodalfit
      </text>
    </svg>
  );
}

// ───── REGISTRATION (concept 09) ──────────────────────────────
export function JodalfitRegistrationSymbol({
  className,
  strokeWidth = 10,
}: {
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      viewBox="0 0 200 200"
      className={className}
      role="img"
      aria-label="jodalfit"
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="butt"
      >
        <polyline points="30 65, 30 30, 65 30" />
        <polyline points="135 30, 170 30, 170 65" />
        <polyline points="170 135, 170 170, 135 170" />
        <polyline points="65 170, 30 170, 30 135" />
      </g>
      <circle cx="100" cy="100" r="13" fill="currentColor" />
    </svg>
  );
}

export function JodalfitRegistrationWordmark({
  className,
  strokeWidth = 10,
}: {
  className?: string;
  strokeWidth?: number;
}) {
  return (
    <svg
      viewBox="0 0 720 200"
      className={className}
      role="img"
      aria-label="jodalfit"
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="butt"
      >
        <polyline points="30 65, 30 30, 65 30" />
        <polyline points="135 30, 170 30, 170 65" />
        <polyline points="170 135, 170 170, 135 170" />
        <polyline points="65 170, 30 170, 30 135" />
      </g>
      <circle cx="100" cy="100" r="13" fill="currentColor" />
      <text
        x="220"
        y="138"
        fill="currentColor"
        fontFamily="Manrope, 'Pretendard Variable', Pretendard, system-ui, -apple-system, 'Segoe UI', sans-serif"
        fontWeight="700"
        fontSize="120"
        letterSpacing="-5"
      >
        jodalfit
      </text>
    </svg>
  );
}

// ───── Default exports — current concept ──────────────────────
export const JodalfitSymbol = JodalfitHalvesSymbol;
export const JodalfitWordmark = JodalfitHalvesWordmark;

// ───── Brand wrapper ──────────────────────────────────────────
export function Brand({
  className,
  size = "md",
  href = "/",
  variant = "wordmark",
  concept = "halves",
}: {
  className?: string;
  size?: "sm" | "md" | "lg";
  href?: string | null;
  variant?: "wordmark" | "symbol";
  concept?: "halves" | "registration";
}) {
  const heights = {
    sm: variant === "symbol" ? "h-6 w-6" : "h-6",
    md: variant === "symbol" ? "h-8 w-8" : "h-8",
    lg: variant === "symbol" ? "h-11 w-11" : "h-11",
  };

  // Halves uses stroke 9, Registration uses stroke 10. Optical adjust for small sizes.
  const stroke =
    concept === "halves"
      ? size === "sm"
        ? 11
        : size === "md"
          ? 10
          : 9
      : size === "sm"
        ? 13
        : size === "md"
          ? 11
          : 10;

  const Symbol =
    concept === "halves" ? JodalfitHalvesSymbol : JodalfitRegistrationSymbol;
  const Wordmark =
    concept === "halves"
      ? JodalfitHalvesWordmark
      : JodalfitRegistrationWordmark;

  const content =
    variant === "symbol" ? (
      <Symbol
        className={cn("text-primary shrink-0", heights[size], className)}
        strokeWidth={stroke}
      />
    ) : (
      <Wordmark
        className={cn("text-primary shrink-0 w-auto", heights[size], className)}
        strokeWidth={stroke}
      />
    );

  if (!href) return content;
  return (
    <Link
      href={href}
      className="inline-flex items-center hover:opacity-80 transition-opacity"
      aria-label="jodalfit 홈"
    >
      {content}
    </Link>
  );
}
