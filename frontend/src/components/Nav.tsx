// frontend/src/components/Nav.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Lockup } from "@/components/Logo";
import { cn } from "@/lib/utils";

export type NavUser = {
  email: string;
  savedCompanies: { bizrnoNorm: string; name: string }[];
  reviewedCount: number;
};

const LINKS = [
  { href: "/recommendations", label: "추천", match: /^\/(recommendations|companies\/[0-9])/ },
  { href: "/saved", label: "검토함", match: /^\/saved/ },
  { href: "/changelog", label: "개선 기록", match: /^\/changelog/ },
];

/** 상단 nav — 비로그인 '로그인' / 로그인됨 you@… + 메뉴(저장한 회사 ★ · 검토함 · 설정 · 로그아웃). 390: 링크 숨김, 현재 페이지와 로그인만. */
export function Nav({ user, signOutHref = "/logout" }: { user?: NavUser | null; signOutHref?: string }) {
  const pathname = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    addEventListener("click", close); addEventListener("keydown", esc);
    return () => { removeEventListener("click", close); removeEventListener("keydown", esc); };
  }, [open]);

  return (
    <div className="rn flex items-center justify-between py-[22px] text-[13px] text-ink-g">
      <Link href="/" aria-label="조달핏 홈"><Lockup /></Link>
      <nav className="flex items-center gap-[22px]" aria-label="주 메뉴">
        {LINKS.map((l) => {
          const active = l.match.test(pathname);
          return (
            <Link key={l.href} href={l.href} aria-current={active ? "page" : undefined}
              className={cn("max-sm:hidden", active && "text-ink font-semibold max-sm:inline")}>
              {l.label}
            </Link>
          );
        })}
        {user ? (
          <div ref={ref} className="relative">
            <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="menu"
              className="text-ink font-semibold border-b border-ink cursor-pointer">
              {user.email.split("@")[0]}@…
            </button>
            {open && (
              <div role="menu" className="absolute right-0 top-7 z-20 min-w-[240px] rounded-[10px] border border-hair bg-panel p-1.5 text-left font-normal shadow-[0_8px_24px_rgba(20,20,20,.06)] max-sm:-right-2">
                <div className="px-3 py-2 text-[13.5px] text-ink">{user.email}<small className="block text-[12px] text-ink-mute">로그인됨</small></div>
                <div className="my-1.5 h-px bg-rule" />
                <span className="t-k block px-3 pb-0.5 pt-2">저장한 회사 {user.savedCompanies.length}</span>
                {user.savedCompanies.map((c) => (
                  <Link key={c.bizrnoNorm} role="menuitem" href={`/companies/${c.bizrnoNorm}`}
                    className="block rounded-md px-3 py-[7px] text-[13.5px] text-ink hover:bg-paper before:mr-2 before:text-[11px] before:text-orange before:content-['★']">
                    {c.name}
                  </Link>
                ))}
                <div className="my-1.5 h-px bg-rule" />
                <Link role="menuitem" href="/saved" className="block rounded-md px-3 py-2 text-[13.5px] text-ink hover:bg-paper">
                  검토함<small className="block text-[12px] text-ink-mute">검토한 공고 {user.reviewedCount}건</small>
                </Link>
                <Link role="menuitem" href="/settings" className="block rounded-md px-3 py-2 text-[13.5px] text-ink hover:bg-paper">
                  설정<small className="block text-[12px] text-ink-mute">비밀번호 변경 · 알림 수신 · 탈퇴</small>
                </Link>
                <div className="my-1.5 h-px bg-rule" />
                <Link role="menuitem" href={signOutHref} className="block rounded-md px-3 py-2 text-[13.5px] text-ink-mute hover:bg-paper">로그아웃</Link>
              </div>
            )}
          </div>
        ) : (
          <Link href={`/login?next=${encodeURIComponent(pathname || "/")}`} className="text-ink border-b border-ink">로그인</Link>
        )}
      </nav>
    </div>
  );
}
