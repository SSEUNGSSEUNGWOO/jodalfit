// frontend/src/components/Nav.tsx
"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Lockup } from "@/components/Logo";
import { cn } from "@/lib/utils";

export type NavUser = {
  email: string;
  savedCompanies: { bizrnoNorm: string; name: string }[];
  reviewedCount: number;
};

// 공고·기업 목록은 그동안 사이트맵과 검색엔진으로만 닿았다(2026-10-26). 회사 상세는 "기업" 아래로 — 전엔 "추천" 이 켜졌다.
const LINKS = [
  { href: "/recommendations", label: "추천", match: /^\/recommendations/ },
  { href: "/notices", label: "공고", match: /^\/notices/ },
  { href: "/companies", label: "기업", match: /^\/companies/ },
  { href: "/saved", label: "검토함", match: /^\/saved/ },
  { href: "/changelog", label: "개선 기록", match: /^\/changelog/ },
];

/** 로그인 링크 — 현재 경로 + 쿼리를 next 로. useSearchParams 는 Suspense 경계가 필요하다(Next 16). */
function LoginLink() {
  const pathname = usePathname() ?? "/";
  const search = useSearchParams()?.toString();
  const next = search ? `${pathname}?${search}` : pathname;
  return <Link href={`/login?next=${encodeURIComponent(next)}`} className="text-ink border-b border-ink transition-colors duration-150 hover:border-orange">로그인</Link>;
}

/** 바깥 클릭·Esc 로 닫히는 팝오버 상태. 사용자 메뉴와 모바일 메뉴가 같이 쓴다. */
function usePopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); trigger.current?.focus(); } };
    addEventListener("click", close); addEventListener("keydown", esc);
    return () => { removeEventListener("click", close); removeEventListener("keydown", esc); };
  }, [open]);
  return { open, setOpen, ref, trigger };
}

const POPOVER = "absolute right-0 top-7 z-20 min-w-[240px] rounded-[10px] border border-hair bg-panel p-1.5 text-left font-normal shadow-[0_8px_24px_rgba(20,20,20,.06)] max-sm:-right-2";

/** 상단 nav — 비로그인 '로그인' / 로그인됨 you@… + 팝오버(저장한 회사 ★ · 검토함 · 로그아웃). 링크 묶음이라 role=menu 는 쓰지 않는다.
 *  390 에서는 섹션 링크를 햄버거(≡) 안에 넣는다 — 항목이 여섯이 되면서(2026-10-26) 활성 하나만 보여주던 방식으론 다른 섹션에 갈 길이 없었다. */
export function Nav({ user, signOutHref = "/logout" }: { user?: NavUser | null; signOutHref?: string }) {
  const pathname = usePathname() ?? "";
  const { open, setOpen, ref, trigger } = usePopover();
  const { open: mOpen, setOpen: setMOpen, ref: mRef, trigger: mTrigger } = usePopover();

  return (
    // 머리 아래 헤어라인 한 줄로 본문과 나눈다(2026-10-28, 승우님) — 색 면은 두지 않는다(주황은 선). 메뉴는 hover 에 먹 글자 + 주황 밑줄(.u-link 와 같은 말).
    <div data-nav className="flex items-center justify-between border-b border-hair py-[22px] text-[13px] text-ink-g print:hidden">
      <Link href="/" aria-label="조달핏 홈"><Lockup /></Link>
      <nav className="flex items-center gap-[22px] max-sm:gap-4" aria-label="주 메뉴">
        {LINKS.map((l) => {
          const active = l.match.test(pathname);
          return (
            <Link key={l.href} href={l.href} aria-current={active ? "page" : undefined}
              className={cn("max-sm:hidden border-b-2 border-transparent pb-px transition-colors duration-150 hover:border-orange hover:text-ink", active && "text-ink font-semibold")}>
              {l.label}
            </Link>
          );
        })}
        {user ? (
          <div ref={ref} className="relative">
            <button ref={trigger} type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="nav-user-menu"
              className="text-ink font-semibold border-b border-ink cursor-pointer transition-colors duration-150 hover:border-orange">
              {user.email.split("@")[0]}@…
            </button>
            {open && (
              <div id="nav-user-menu" data-menu className={POPOVER}>
                <div className="px-3 py-2 text-[13.5px] text-ink">{user.email}<small className="block text-[12px] text-ink-mute">로그인됨</small></div>
                <div className="my-1.5 h-px bg-rule" />
                <span className="t-k block px-3 pb-0.5 pt-2">저장한 회사 {user.savedCompanies.length}</span>
                {user.savedCompanies.map((c) => (
                  <Link key={c.bizrnoNorm} href={`/companies/${c.bizrnoNorm}`}
                    className="block rounded-md px-3 py-[7px] text-[13.5px] text-ink hover:bg-paper before:mr-2 before:text-[11px] before:text-orange-ink before:content-['★']">
                    {c.name}
                  </Link>
                ))}
                <div className="my-1.5 h-px bg-rule" />
                <Link href="/saved" className="block rounded-md px-3 py-2 text-[13.5px] text-ink hover:bg-paper">
                  검토함<small className="block text-[12px] text-ink-mute">검토한 공고 {user.reviewedCount}건</small>
                </Link>
                <div className="my-1.5 h-px bg-rule" />
                <a href={signOutHref} className="block rounded-md px-3 py-2 text-[13.5px] text-ink-mute hover:bg-paper">로그아웃</a>
              </div>
            )}
          </div>
        ) : (
          <Suspense fallback={<span className="text-ink border-b border-ink">로그인</span>}><LoginLink /></Suspense>
        )}
        {/* 모바일 섹션 메뉴 — 데스크톱에선 링크가 다 보이므로 숨긴다 */}
        <div ref={mRef} className="relative sm:hidden">
          <button ref={mTrigger} type="button" data-nav-menu onClick={() => setMOpen((v) => !v)} aria-expanded={mOpen} aria-controls="nav-section-menu" aria-label="메뉴"
            className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-ink hover:bg-paper">
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              {mOpen ? <path d="M4 4l10 10M14 4L4 14" /> : <path d="M2.5 5h13M2.5 9h13M2.5 13h13" />}
            </svg>
          </button>
          {mOpen && (
            <div id="nav-section-menu" data-section-menu className={cn(POPOVER, "min-w-[180px]")}>
              {LINKS.map((l) => {
                const active = l.match.test(pathname);
                return (
                  <Link key={l.href} href={l.href} aria-current={active ? "page" : undefined} onClick={() => setMOpen(false)}
                    className={cn("block rounded-md px-3 py-2 text-[14px] text-ink hover:bg-paper", active && "font-semibold")}>
                    {l.label}
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </nav>
    </div>
  );
}
