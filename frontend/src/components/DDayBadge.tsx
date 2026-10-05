"use client";

import { Badge } from "@/components/ui/badge";
import { useToday } from "@/lib/use-today";
import { cn, daysUntil, formatDateKR } from "@/lib/utils";

/** 서버 렌더(ISR 캐시 HTML)에는 날짜만 들어가고, D-n 라벨은 브라우저에서 오늘을 안 뒤 붙는다.
 *  라벨을 서버에서 계산하면 공고 내용이 그대로여도 매일 HTML이 바뀌어 ISR Write가 난다. */
export function DDayBadge({
  date,
  className,
}: {
  date: string | null | undefined;
  className?: string;
}) {
  const today = useToday();
  if (!date) return null;
  const days = today ? daysUntil(date, today) : null;

  let variant: "destructive" | "secondary" | "default" | "outline" = "secondary";
  let label = days === null ? null : `D-${days}`;
  let tint: string | undefined;

  if (days === null) {
    // 오늘을 아직 모름(서버·하이드레이션 중) — 날짜만 중립 표시
  } else if (days < 0) {
    variant = "outline";
    label = "마감됨";
  } else if (days === 0) {
    variant = "destructive";
    label = "오늘 마감";
  } else if (days <= 2) {
    variant = "destructive";
    label = `D-${days}`;
  } else if (days <= 5) {
    variant = "secondary";
    tint = "bg-orange-100 text-orange-700 border-orange-200";
  }

  return (
    <Badge
      variant={variant}
      className={cn("gap-2 font-bold tabular tabular-nums", tint, className)}
    >
      {label && <span>{label}</span>}
      <span className="text-[11px] font-medium opacity-70">
        {formatDateKR(date)}
      </span>
    </Badge>
  );
}
