import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function EvidenceTag({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Badge
      variant="secondary"
      className={cn(
        "bg-primary/10 text-primary hover:bg-primary/15 font-semibold",
        className
      )}
    >
      {children}
    </Badge>
  );
}
