"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { JodalfitSymbol } from "@/components/Brand";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/notices", label: "공고 둘러보기" },
  { href: "/insights", label: "주간 인사이트" },
  { href: "/about", label: "조달핏이란" },
];

const CONTACT_HREF =
  "mailto:jsw7980@gmail.com?subject=%EC%A1%B0%EB%8B%AC%ED%95%8F%20%EC%9D%98%EA%B2%AC";

export function Header() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <header className="world-gc sticky top-0 z-40 bg-gc-paper">
      <div className="mx-auto flex h-16 max-w-[1080px] items-center justify-between px-5 sm:px-8">
        <Link href="/" className="flex items-center gap-2">
          <JodalfitSymbol className="h-[22px] w-[22px] text-gc-band shrink-0" />
          <span className="font-gc-serif font-black text-[21px] tracking-[-0.02em] text-gc-ink leading-none">
            조달핏
          </span>
          <span className="hidden sm:inline self-end pb-px text-[11px] font-semibold tracking-wide text-gc-ink-3">
            우리 회사에 맞는 공공입찰
          </span>
        </Link>

        <nav className="hidden sm:flex items-center gap-0.5" aria-label="주 메뉴">
          {NAV_ITEMS.map((it) => {
            const active = pathname?.startsWith(it.href);
            return (
              <Link
                key={it.href}
                href={it.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "px-3 py-2 text-[13.5px] font-bold transition-colors border-b-2",
                  active
                    ? "text-gc-ink border-gc-band"
                    : "text-gc-ink-2 border-transparent hover:text-gc-ink hover:border-gc-rule"
                )}
              >
                {it.label}
              </Link>
            );
          })}
          <Link
            href={CONTACT_HREF}
            title="jsw7980@gmail.com"
            className="ml-1 px-3 py-2 text-[13.5px] font-bold text-gc-ink-2 border-b-2 border-transparent hover:text-gc-ink hover:border-gc-rule transition-colors"
          >
            문의
          </Link>
        </nav>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls="gc-mobile-nav"
          aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
          className="sm:hidden inline-flex h-10 w-10 items-center justify-center text-gc-ink"
        >
          {open ? (
            <X className="h-5 w-5" aria-hidden />
          ) : (
            <Menu className="h-5 w-5" aria-hidden />
          )}
        </button>
      </div>

      {/* 모바일 메뉴 */}
      <div
        id="gc-mobile-nav"
        className={cn("sm:hidden gc-open-wrap", open && "border-t border-gc-rule")}
        data-open={open}
      >
        <nav className="gc-open-inner" aria-label="모바일 메뉴">
          <div className="px-5 py-2 bg-gc-sheet">
            {NAV_ITEMS.map((it) => (
              <Link
                key={it.href}
                href={it.href}
                onClick={() => setOpen(false)}
                className="block py-3 text-[15px] font-bold text-gc-ink border-b border-gc-rule last:border-b-0"
              >
                {it.label}
              </Link>
            ))}
            <Link
              href={CONTACT_HREF}
              onClick={() => setOpen(false)}
              className="block py-3 text-[15px] font-bold text-gc-ink-2"
            >
              문의
            </Link>
          </div>
        </nav>
      </div>

      {/* 관보식 이중 괘선 — .gc-double-rule은 position:relative로 sticky를 깨뜨려 별도 요소로 그림 */}
      <div aria-hidden>
        <div className="border-t-2 border-gc-ink" />
        <div className="mt-px border-t border-gc-ink" />
      </div>
    </header>
  );
}
