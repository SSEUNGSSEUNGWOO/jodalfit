import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Narrow } from "@/components/Narrow";
import { getSessionUser } from "@/lib/auth";
import { safeNext } from "@/lib/safe-next";
import { SignupForm } from "./SignupForm";

export const metadata: Metadata = { title: "회원가입 | 조달핏", robots: { index: false, follow: false } };

export default async function SignupPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const next = safeNext((await searchParams).next);
  if (await getSessionUser()) redirect(next);
  return <Narrow title="회원가입"><SignupForm next={next} /></Narrow>;
}
