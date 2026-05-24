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

  const dims = {
    sm: { num: "text-[24px]", w: "w-14", h: "h-1.5", lbl: "text-[11.5px]" },
    md: { num: "text-[36px]", w: "w-20", h: "h-2", lbl: "text-[12.5px]" },
    lg: { num: "text-[52px]", w: "w-28", h: "h-2.5", lbl: "text-[13px]" },
  }[size];

  return (
    <div className={cn("flex flex-col items-end gap-2", className)}>
      <div className="flex items-baseline gap-1">
        <span
          className={cn(
            "font-extrabold tabular tabular-nums leading-none text-primary",
            dims.num
          )}
        >
          {pct}
        </span>
        <span className="text-sm font-semibold text-muted-foreground">점</span>
      </div>
      <div
        className={cn(
          "relative overflow-hidden rounded-full bg-muted",
          dims.w,
          dims.h
        )}
      >
        <div
          className="absolute inset-y-0 left-0 bg-primary rounded-full"
          style={{ width: `${pct}%` }}
          aria-hidden
        />
      </div>
      <span className={cn("font-bold text-primary", dims.lbl)}>{label}</span>
    </div>
  );
}
