// frontend/src/components/Logo.tsx
import { cn } from "@/lib/utils";

/** 마크 — ㄱㄴ 틀 "찰칵". currentColor. 20px 미만은 Mark16. (docs/design/brand/mark.svg) */
export function Mark({ className, size = 22 }: { className?: string; size?: number }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} fill="none" aria-hidden="true" className={className}>
      <path d="M30 14 H50 V34 M14 30 V50 H34" stroke="currentColor" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 16px 정수 격자 쌍둥이 — 획 3, 틈 1, 둥근 끝 없음. (brand/mark-16.svg) */
export function Mark16({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" width={16} height={16} aria-hidden="true" className={className}>
      <path d="M6 2h8v3H6zM11 2h3v8h-3zM2 6h3v8H2zM2 11h8v3H2z" fill="currentColor" />
    </svg>
  );
}

/** 주황 타일 + 흰 마크 — "주황은 선" 규칙의 유일한 예외(로고 타일). nav 22 · 히어로 48. (brand/tile.svg) */
export function Tile({ size = 22, className }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" className={className}>
      <rect width="64" height="64" rx="14.08" fill="#f97316" />
      <path d="M30 14 H50 V34 M14 30 V50 H34" fill="none" stroke="#fff" strokeWidth="11" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 타일 22 + 조달핏(Pretendard 800, 16px, 자간 −0.035em). */
export function Lockup({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-ink font-extrabold text-[16px] tracking-[-0.035em] leading-none", className)}>
      <Tile size={22} />
      조달핏
    </span>
  );
}
