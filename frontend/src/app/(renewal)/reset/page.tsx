import type { Metadata } from "next";
import { Narrow } from "@/components/Narrow";
import { ResetForm } from "./ResetForm";

export const metadata: Metadata = { title: "비밀번호 재설정 | 조달핏", robots: { index: false, follow: false } };

export default async function ResetPage({ searchParams }: { searchParams: Promise<{ email?: string }> }) {
  return <Narrow title="비밀번호 재설정"><ResetForm initialEmail={(await searchParams).email ?? ""} /></Narrow>;
}
