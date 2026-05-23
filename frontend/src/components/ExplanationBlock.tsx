import { Quote } from "lucide-react";
import { cn } from "@/lib/utils";

export function ExplanationBlock({
  text,
  className,
  label = "추천 이유",
}: {
  text: string;
  className?: string;
  label?: string;
}) {
  return (
    <div
      className={cn(
        "quote-rail bg-bg-alt/60 rounded-tile py-3 pr-4",
        className
      )}
    >
      <div className="flex items-center gap-1.5">
        <Quote
          className="h-3 w-3 text-teal-600 rotate-180"
          aria-hidden
          strokeWidth={2.5}
        />
        <span className="eyebrow text-teal-700">{label}</span>
      </div>
      <p className="mt-1.5 text-[14.5px] leading-[1.65] text-ink">{text}</p>
    </div>
  );
}
