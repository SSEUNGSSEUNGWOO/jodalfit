import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  /** 1-based */
  current: number;
  totalPages: number;
  /** href는 page 번호를 받아 URL을 만듭니다 */
  hrefFor: (page: number) => string;
  /** 가운데 표시할 페이지 윈도우 크기 (current 양쪽 합산) */
  window?: number;
}

export function Pagination({
  current,
  totalPages,
  hrefFor,
  window: w = 2,
}: Props) {
  if (totalPages <= 1) return null;

  const numbers: number[] = [];
  const start = Math.max(2, current - w);
  const end = Math.min(totalPages - 1, current + w);
  for (let i = start; i <= end; i++) numbers.push(i);

  const showLeftEllipsis = start > 2;
  const showRightEllipsis = end < totalPages - 1;

  return (
    <nav
      aria-label="페이지네이션"
      className="mt-10 flex items-center justify-center gap-1.5"
    >
      <PageLink
        href={hrefFor(Math.max(1, current - 1))}
        disabled={current === 1}
        label="이전 페이지"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden />
      </PageLink>

      <NumberLink page={1} current={current} hrefFor={hrefFor} />
      {showLeftEllipsis && <Ellipsis />}
      {numbers.map((n) => (
        <NumberLink key={n} page={n} current={current} hrefFor={hrefFor} />
      ))}
      {showRightEllipsis && <Ellipsis />}
      {totalPages > 1 && (
        <NumberLink page={totalPages} current={current} hrefFor={hrefFor} />
      )}

      <PageLink
        href={hrefFor(Math.min(totalPages, current + 1))}
        disabled={current === totalPages}
        label="다음 페이지"
      >
        <ChevronRight className="h-4 w-4" aria-hidden />
      </PageLink>
    </nav>
  );
}

function NumberLink({
  page,
  current,
  hrefFor,
}: {
  page: number;
  current: number;
  hrefFor: (n: number) => string;
}) {
  const isActive = page === current;
  return (
    <Link
      href={hrefFor(page)}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "min-w-[36px] h-9 px-2 inline-flex items-center justify-center rounded-md text-[13.5px] font-semibold tabular-nums transition-colors",
        isActive
          ? "bg-primary text-primary-foreground"
          : "bg-background border border-border text-foreground hover:bg-muted"
      )}
    >
      {page}
    </Link>
  );
}

function PageLink({
  href,
  disabled,
  label,
  children,
}: {
  href: string;
  disabled: boolean;
  label: string;
  children: React.ReactNode;
}) {
  if (disabled) {
    return (
      <span
        aria-disabled
        className="min-w-[36px] h-9 inline-flex items-center justify-center rounded-md border border-border bg-muted/40 text-muted-foreground/50"
        title={label}
      >
        {children}
      </span>
    );
  }
  return (
    <Link
      href={href}
      aria-label={label}
      className="min-w-[36px] h-9 inline-flex items-center justify-center rounded-md border border-border bg-background text-foreground hover:bg-muted transition-colors"
    >
      {children}
    </Link>
  );
}

function Ellipsis() {
  return (
    <span
      aria-hidden
      className="min-w-[28px] inline-flex items-center justify-center text-muted-foreground/70 select-none"
    >
      …
    </span>
  );
}
