import { cn, scoreLabel, scorePercent } from "@/lib/utils";

export function MatchScore({
  score,
  size = "md",
  className,
}: {
  score: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const { label } = scoreLabel(score);
  const pct = scorePercent(score);
  const fill = Math.min(100, Math.max(0, pct));

  const dims = {
    sm: { number: "text-[22px]", label: "text-[11px]", width: "w-12" },
    md: { number: "text-[32px]", label: "text-[12px]", width: "w-16" },
    lg: { number: "text-[44px]", label: "text-[12px]", width: "w-20" },
  }[size];

  return (
    <div className={cn("flex flex-col items-end gap-1.5", className)}>
      <div className="flex items-baseline gap-1">
        <span
          className={cn(
            "font-bold tabular text-navy leading-none",
            dims.number
          )}
        >
          {pct}
        </span>
        <span className="text-[12px] font-medium text-ink-muted">/ 100</span>
      </div>
      <div className={cn("gauge-track", dims.width)}>
        <div
          className="gauge-fill draw"
          style={{
            transform: `scaleX(${fill / 100})`,
            transformOrigin: "left",
          }}
          aria-hidden
        />
      </div>
      <span
        className={cn(
          "eyebrow tabular text-teal-700",
          dims.label
        )}
      >
        {label}
      </span>
    </div>
  );
}
