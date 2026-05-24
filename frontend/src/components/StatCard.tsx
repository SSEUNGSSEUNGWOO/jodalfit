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
    <div className={cn("", className)}>
      <span className="text-sm font-semibold text-muted-foreground">{label}</span>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-[36px] sm:text-[40px] font-extrabold tabular tabular-nums leading-none text-foreground">
          {value}
        </span>
        {suffix && (
          <span className="text-base font-bold text-muted-foreground">
            {suffix}
          </span>
        )}
      </div>
      {hint && (
        <p className="mt-2 text-xs text-muted-foreground/70">{hint}</p>
      )}
    </div>
  );
}
