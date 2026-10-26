"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/** 의견 보내기 링크 — 지금 보던 경로를 ?from= 으로 넘긴다(오류 제보가 어느 화면 얘기인지). 클라이언트 라우팅에서는
 *  document.referrer 가 갱신되지 않아 쓸 수 없다(2026-10-26). /feedback 자신에서는 from 을 붙이지 않는다. */
export function FeedbackLink({ className, children }: { className?: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const from = pathname && pathname !== "/feedback" ? `?from=${encodeURIComponent(pathname)}` : "";
  return <Link href={`/feedback${from}`} className={className}>{children}</Link>;
}
