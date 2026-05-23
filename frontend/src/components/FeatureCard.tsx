import { cn } from "@/lib/utils";

export function FeatureCard({
  index,
  eyebrow,
  title,
  body,
  className,
}: {
  index: string;
  eyebrow: string;
  title: string;
  body: string;
  className?: string;
}) {
  return (
    <article
      className={cn(
        "group relative inset-card flex flex-col p-7 transition-transform hover:-translate-y-0.5",
        className
      )}
    >
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[12px] font-bold tabular text-teal-600">
          {index}
        </span>
        <span className="eyebrow text-ink-muted">{eyebrow}</span>
      </div>
      <h3 className="mt-4 text-[19px] font-bold leading-snug text-ink-strong">
        {title}
      </h3>
      <p className="mt-2.5 text-[14.5px] leading-[1.65] text-ink-muted">
        {body}
      </p>
      {/* Bottom hairline accent */}
      <div className="mt-5 h-px w-12 bg-teal-500 transition-all group-hover:w-16" />
    </article>
  );
}
