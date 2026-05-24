import { Badge } from "@/components/ui/badge";
import { cn, daysUntil, formatDateKR } from "@/lib/utils";

export function DDayBadge({
  date,
  className,
}: {
  date: string | null | undefined;
  className?: string;
}) {
  const days = daysUntil(date);
  if (days === null) return null;

  let variant: "destructive" | "secondary" | "default" | "outline" = "secondary";
  let label = `D-${days}`;
  let tint: string | undefined;

  if (days < 0) {
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
      <span>{label}</span>
      <span className="text-[11px] font-medium opacity-70">
        {formatDateKR(date)}
      </span>
    </Badge>
  );
}
