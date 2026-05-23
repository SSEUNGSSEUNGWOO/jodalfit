import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  suffix,
  hint,
  className,
}: {
  label: string;
  value: string;
  suffix?: string;
  hint?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col justify-between gap-4 border-l border-line pl-5 first:border-l-0 first:pl-0",
        "sm:pl-6 sm:first:pl-0",
        className
      )}
    >
      <span className="eyebrow text-ink-muted">{label}</span>
      <div className="flex items-baseline gap-1">
        <span className="text-[28px] font-bold tabular leading-none text-navy sm:text-[32px]">
          {value}
        </span>
        {suffix && (
          <span className="text-[14px] font-semibold text-ink-muted">
            {suffix}
          </span>
        )}
      </div>
      {hint && <span className="text-[12px] text-ink-soft">{hint}</span>}
    </div>
  );
}
