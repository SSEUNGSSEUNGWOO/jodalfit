import Link from "next/link";
import { Brand } from "./Brand";

export function Header() {
  return (
    <header className="sticky top-0 z-40 bg-bg/90 backdrop-blur-md border-b border-line">
      <div className="mx-auto flex h-16 max-w-[1140px] items-center justify-between px-5 sm:px-8">
        <Brand size="md" />
        <nav className="flex items-center gap-2 sm:gap-1">
          <Link
            href="/#how"
            className="hidden sm:inline-block px-3 py-2 text-[14px] font-semibold text-ink-3 hover:text-ink rounded-md hover:bg-bg-soft transition-colors"
          >
            추천 방식
          </Link>
          <Link
            href="mailto:hello@jodalfit.co.kr"
            className="px-3 py-2 text-[14px] font-semibold text-ink-3 hover:text-ink rounded-md hover:bg-bg-soft transition-colors"
          >
            문의
          </Link>
        </nav>
      </div>
    </header>
  );
}
