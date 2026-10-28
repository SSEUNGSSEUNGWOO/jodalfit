import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { SocialButtons } from "@/components/SocialButtons";
import { getSessionUser } from "@/lib/auth";
import { safeNext } from "@/lib/safe-next";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = { title: "로그인 | 조달핏", robots: { index: false, follow: false } };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; error?: string }> }) {
  const p = await searchParams;
  const next = safeNext(p.next);
  if (await getSessionUser()) redirect(next);
  return (
    <Narrow title="로그인">
      <SocialButtons next={next} from="login" />
      <LoginForm next={next} linkError={p.error === "link"} oauthError={p.error === "oauth"} />
    </Narrow>
  );
}
