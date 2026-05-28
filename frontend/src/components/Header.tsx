import Link from "next/link";
import { Brand } from "./Brand";

const NAV_ITEMS = [
  { href: "/notices", label: "공고 둘러보기" },
  { href: "/insights", label: "주간 인사이트" },
  { href: "/about", label: "jodalfit이란" },
];

export function Header() {
  return (
    <header className="sticky top-0 z-40 bg-background/90 backdrop-blur-md border-b border-border">
      <div className="mx-auto flex h-16 max-w-[1140px] items-center justify-between px-5 sm:px-8">
        <Brand size="md" />
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((it) => (
            <Link
              key={it.href}
              href={it.href}
              className="hidden sm:inline-flex px-3 py-2 text-[14px] font-semibold text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
            >
              {it.label}
            </Link>
          ))}
          <Link
            href="mailto:jsw7980@gmail.com"
            className="px-3 py-2 text-[14px] font-semibold text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
          >
            문의
          </Link>
        </nav>
      </div>
    </header>
  );
}
