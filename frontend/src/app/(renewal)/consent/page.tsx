// frontend/src/app/(renewal)/consent/page.tsx
// 소셜 가입 마무리 한 판(2026-10-28) — 가입 폼을 안 거친 계정(구글·네이버 OAuth)은 user_consents 가 ''/'' 로 생긴다(0052 트리거).
// auth/callback 이 lib/after-auth 로 여기 보낸다. 동의(필수)와 우리 회사 저장(선택)을 한 화면에 — 저장 회사가 이미 있으면 회사 칸은 뺀다.
// 이미 동의한 계정이면 next 로. 비로그인은 로그인으로. 이메일 가입은 가입 폼에서 동의를 받으므로 여기 안 온다(/welcome 만).
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { getSessionUser } from "@/lib/auth";
import { safeNext } from "@/lib/safe-next";
import { getSavedCompanyKeys } from "@/lib/saved";
import { getServerSupabase } from "@/lib/supabase/server";
import { ConsentForm } from "./ConsentForm";

export const metadata: Metadata = { title: "가입 마무리 | 조달핏", robots: { index: false, follow: false } };

export default async function ConsentPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const next = safeNext((await searchParams).next);
  const user = await getSessionUser();
  if (!user) redirect(`/login?next=${encodeURIComponent(`/consent?next=${encodeURIComponent(next)}`)}`);
  const [{ data }, saved] = await Promise.all([
    (await getServerSupabase()).from("user_consents").select("terms_version").maybeSingle(),
    getSavedCompanyKeys(),
  ]);
  if (data && data.terms_version !== "") redirect(next);
  return (
    <Narrow title="가입 마무리">
      <p data-consent className="m-0 mb-1 text-[14.5px] leading-[1.75] text-ink-body">
        <b className="font-semibold text-ink">{user.email}</b> 계정으로 처음 로그인했습니다. 아래 두 항목에 동의하면 바로 시작합니다.
      </p>
      <ConsentForm next={next} showCompany={saved.size === 0} />
    </Narrow>
  );
}
