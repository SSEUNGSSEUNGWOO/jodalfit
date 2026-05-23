import { cn } from "@/lib/utils";

export function EvidenceTag({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-tile border border-line bg-bg-alt px-2 py-0.5 text-[12px] font-medium text-ink-muted",
        "transition-colors hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700",
        className
      )}
    >
      <span className="text-teal-500">#</span>
      <span className="ml-0.5">{children}</span>
    </span>
  );
}
