// frontend/src/app/(renewal)/layout.tsx
import type { ReactNode } from "react";
import { Nav } from "@/components/Nav";
import { SiteFooter } from "@/components/SiteFooter";
import { getNavUser } from "@/lib/auth";

/** 리뉴얼 페이지 공용 — 바닥(paper) + Nav(세션) + 바닥글. 옛 페이지는 09 컷오버에서 이 아래로 옮긴다. */
export default async function RenewalLayout({ children }: { children: ReactNode }) {
  const user = await getNavUser();
  return (
    <div className="rn min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1120px] px-5 pb-[120px]">
        <Nav user={user} />
        {children}
        <SiteFooter />
      </div>
    </div>
  );
}
