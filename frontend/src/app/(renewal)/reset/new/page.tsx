import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { getSessionUser } from "@/lib/auth";
import { NewPasswordForm } from "./NewPasswordForm";

export const metadata: Metadata = { title: "새 비밀번호 | 조달핏", robots: { index: false, follow: false } };

/** recovery 링크를 연 상태(세션 있음)에서만. 세션이 없으면 재설정 처음으로. */
export default async function NewPasswordPage() {
  const user = await getSessionUser();
  if (!user) redirect("/reset");
  return <Narrow title="새 비밀번호"><NewPasswordForm email={user.email} /></Narrow>;
}
