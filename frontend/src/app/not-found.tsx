// frontend/src/app/not-found.tsx
// 없는 주소의 404 — 루트 레이아웃 안에서만 그려져 (renewal) 레이아웃의 nav·바닥글이 없다. 그래서 로고 줄을 직접 둔다.
// 그 전엔 Next 기본 404(영문 "This page could not be found.")가 옛 폴백 메타와 함께 나갔다(2026-10-25).
import type { Metadata } from "next";
import Link from "next/link";
import { Lockup } from "@/components/Logo";
import { NotFoundBlock } from "@/components/NotFoundBlock";

export const metadata: Metadata = { title: "페이지가 없습니다 | 조달핏", robots: { index: false, follow: false } };

export default function NotFound() {
  return (
    <div className="rn min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1120px] px-5 pb-[120px]">
        <div className="flex h-[64px] items-center"><Link href="/" aria-label="조달핏 홈"><Lockup /></Link></div>
        <main id="main"><NotFoundBlock /></main>
      </div>
    </div>
  );
}
