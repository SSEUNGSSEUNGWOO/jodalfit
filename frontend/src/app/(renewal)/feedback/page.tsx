// frontend/src/app/(renewal)/feedback/page.tsx
// 의견 보내기 — 가입 없이 의견·문의·오류 제보를 남긴다. 백엔드 POST /feedback(0061) 에 저장, /admin 에서 읽는다.
// ?from=/경로 = 폼을 연 직전 화면(FeedbackLink 가 붙인다). 로그인 상태면 답장 주소를 미리 채운다. 색인 제외.
import type { Metadata } from "next";
import { Narrow } from "@/components/Narrow";
import { getSessionUser } from "@/lib/auth";
import { FeedbackForm } from "./FeedbackForm";

export const metadata: Metadata = { title: "의견 보내기 | 조달핏", robots: { index: false, follow: false } };

type Props = { searchParams: Promise<{ from?: string }> };

export default async function FeedbackPage({ searchParams }: Props) {
  const [user, sp] = await Promise.all([getSessionUser(), searchParams]);
  // 같은 사이트 경로만(열린 리다이렉트는 아니지만 아무 문자열을 저장하지 않는다)
  const from = sp.from && /^\/[^\s]{0,400}$/.test(sp.from) && !sp.from.startsWith("//") ? sp.from : null;
  return (
    <Narrow title="의견 보내기">
      <FeedbackForm initialEmail={user?.email ?? ""} page={from} />
    </Narrow>
  );
}
