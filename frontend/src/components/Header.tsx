import Link from "next/link";
import { Brand } from "./Brand";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1180px] items-center justify-between px-6 sm:px-8">
        <Brand size="md" />
        <nav className="flex items-center gap-7 text-[14px] text-ink-muted">
          <Link
            href="/#how"
            className="hidden transition-colors hover:text-ink sm:inline"
          >
            추천 방식
          </Link>
          <Link
            href="/#trust"
            className="hidden transition-colors hover:text-ink sm:inline"
          >
            데이터
          </Link>
          <Link
            href="mailto:hello@jodalfit.co.kr"
            className="transition-colors hover:text-ink"
          >
            문의
          </Link>
        </nav>
      </div>
    </header>
  );
}
