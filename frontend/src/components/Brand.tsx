import Link from "next/link";
import { cn } from "@/lib/utils";

export function Brand({
  className,
  size = "md",
  href = "/",
}: {
  className?: string;
  size?: "sm" | "md" | "lg";
  href?: string | null;
}) {
  const sizes = {
    sm: "text-[15px]",
    md: "text-[17px]",
    lg: "text-[22px]",
  };
  const content = (
    <span
      className={cn(
        "inline-flex items-baseline font-semibold tracking-tight text-navy",
        sizes[size],
        className
      )}
    >
      jodalfit
      <span
        aria-hidden
        className="ml-1 inline-block h-1.5 w-1.5 translate-y-[-2px] rounded-full bg-teal-500"
      />
    </span>
  );
  if (!href) return content;
  return <Link href={href}>{content}</Link>;
}
