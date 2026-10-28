// frontend/src/app/(renewal)/welcome/page.tsx
// 가입 확인 직후 한 판 — 저장한 회사가 0곳이면 우리 회사를 저장하게 한다(2026-10-28). 선택이라 "나중에" 로 next 로 간다.
// auth/confirm 이 signup 확인 뒤 여기로 보낸다(next 에 회사가 없을 때). 이미 저장한 회사가 있으면 next 로 바로 보낸다.
// 가입 폼 안에 회사 칸을 두지 않은 이유: 확인 메일 전엔 계정이 없어 user_metadata 로 들고 있다가 옮기는 우회가 필요하다.
import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { SaveCompanyForm } from "@/components/SaveCompanyForm";
import { getSessionUser } from "@/lib/auth";
import { safeNext } from "@/lib/safe-next";
import { getSavedCompanyKeys } from "@/lib/saved";

export const metadata: Metadata = { title: "우리 회사 저장 | 조달핏", robots: { index: false, follow: false } };

export default async function WelcomePage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const next = safeNext((await searchParams).next);
  const user = await getSessionUser();
  if (!user) redirect(`/login?next=${encodeURIComponent(`/welcome?next=${encodeURIComponent(next)}`)}`);
  if ((await getSavedCompanyKeys()).size > 0) redirect(next);
  // 기본 next(/recommendations → /)면 저장 뒤 검토함으로 — 저장한 행과 주간 메일 토글이 거기 있다.
  const after = next === "/recommendations" || next === "/" ? "/saved" : next;
  return (
    <Narrow title="우리 회사 저장">
      <p data-welcome className="m-0 mb-4 text-[14.5px] leading-[1.75] text-ink-body">
        우리 회사를 저장해 두면 검토함에 회사별 추천이 모이고, 알림 메일에 동의한 경우 새 공고가 있는 주에 월요일 아침 한 통을 보냅니다.
        회사 이름이나 사업자등록번호를 적고 목록에서 고릅니다.
      </p>
      <SaveCompanyForm next={after} from="welcome" />
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]">
        <Link href={next} data-welcome-skip className="u-link text-ink">나중에</Link>
      </div>
    </Narrow>
  );
}
