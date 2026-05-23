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

  let tone: "danger" | "warning" | "ink" | "muted" = "ink";
  let prefix = "D-";
  let n: number | string = days;

  if (days < 0) {
    tone = "muted";
    prefix = "D+";
    n = -days;
  } else if (days === 0) {
    tone = "danger";
    prefix = "D";
    n = "DAY";
  } else if (days <= 2) {
    tone = "danger";
  } else if (days <= 5) {
    tone = "warning";
  }

  const tones = {
    danger: "bg-danger-50 text-danger border-danger/20",
    warning: "bg-warning-50 text-warning border-warning/30",
    ink: "bg-navy-50 text-navy border-navy-100",
    muted: "bg-line-soft text-ink-muted border-line",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-tile border px-2 py-0.5 text-[12px] font-semibold tabular",
        tones[tone],
        className
      )}
    >
      <span>{`${prefix}${n}`}</span>
      <span className="font-normal text-ink-muted">{formatDateKR(date)}</span>
    </span>
  );
}
