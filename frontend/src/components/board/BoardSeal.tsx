import { cn } from "@/lib/utils";

/** 관인(官印) — 개찰판 판머리의 인장. 정방형 인주 도장, 절제된 공식 문서 문법. */
export function BoardSeal({
  size = 64,
  className,
  title = "조달핏 인",
}: {
  size?: number;
  className?: string;
  title?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 72 72"
      role="img"
      aria-label={title}
      className={cn("rotate-[-4deg]", className)}
    >
      {/* 흰 지면 판 — 도장은 어두운 밴드가 아니라 종이 위에 찍힌다 */}
      <rect
        x="0"
        y="0"
        width="72"
        height="72"
        rx="6"
        fill="var(--color-gc-sheet)"
        fillOpacity="0.95"
      />
      <rect
        x="4"
        y="4"
        width="64"
        height="64"
        rx="7"
        fill="none"
        stroke="var(--color-gc-injuk)"
        strokeWidth="4.5"
      />
      <rect
        x="12"
        y="12"
        width="48"
        height="48"
        rx="3"
        fill="none"
        stroke="var(--color-gc-injuk)"
        strokeWidth="1.5"
        opacity="0.55"
      />
      <text
        x="24.5"
        y="31.5"
        textAnchor="middle"
        fontFamily="var(--font-gc-serif)"
        fontWeight="900"
        fontSize="17"
        fill="var(--color-gc-injuk)"
      >
        조
      </text>
      <text
        x="47.5"
        y="31.5"
        textAnchor="middle"
        fontFamily="var(--font-gc-serif)"
        fontWeight="900"
        fontSize="17"
        fill="var(--color-gc-injuk)"
      >
        달
      </text>
      <text
        x="24.5"
        y="55"
        textAnchor="middle"
        fontFamily="var(--font-gc-serif)"
        fontWeight="900"
        fontSize="17"
        fill="var(--color-gc-injuk)"
      >
        핏
      </text>
      {/* 네 번째 칸 — 문자 대신 기하 마크 (채움 사각) */}
      <rect
        x="41"
        y="42.5"
        width="13"
        height="13"
        rx="2"
        fill="var(--color-gc-injuk)"
      />
    </svg>
  );
}

/** 저장 인장 — 행 순번 위에 찍히는 소형 "검토" 도장 */
export function ReviewStamp({ className }: { className?: string }) {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 34 34"
      role="img"
      aria-label="검토 인장"
      className={className}
    >
      <circle
        cx="17"
        cy="17"
        r="14.5"
        fill="var(--color-gc-paper)"
        fillOpacity="0.85"
        stroke="var(--color-gc-injuk)"
        strokeWidth="2.5"
      />
      <text
        x="17"
        y="21.5"
        textAnchor="middle"
        fontFamily="var(--font-gc-serif)"
        fontWeight="900"
        fontSize="11.5"
        fill="var(--color-gc-injuk)"
      >
        검토
      </text>
    </svg>
  );
}
