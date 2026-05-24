import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function ExplanationBlock({
  text,
  className,
  label = "왜 추천했는지",
}: {
  text: string;
  className?: string;
  label?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl bg-primary/5 border border-primary/15 p-5",
        className
      )}
    >
      <div className="flex items-center gap-1.5">
        <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden />
        <span className="text-[12.5px] font-bold text-primary">{label}</span>
      </div>
      <p className="mt-2 text-[14.5px] leading-[1.7] text-foreground/85">{text}</p>
    </div>
  );
}
