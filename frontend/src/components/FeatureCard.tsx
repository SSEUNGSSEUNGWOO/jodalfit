import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function FeatureCard({
  emoji,
  title,
  body,
  className,
}: {
  emoji: string;
  title: string;
  body: string;
  className?: string;
}) {
  return (
    <Card className={cn("h-full transition-shadow hover:shadow-md", className)}>
      <CardContent className="p-7">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-2xl">
          {emoji}
        </div>
        <h3 className="mt-5 text-[20px] font-extrabold tracking-tight text-foreground">
          {title}
        </h3>
        <p className="mt-2.5 text-[15px] leading-[1.65] text-muted-foreground">
          {body}
        </p>
      </CardContent>
    </Card>
  );
}
