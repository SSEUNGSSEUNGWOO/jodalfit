"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Btn } from "@/components/Btn";
import { TextField } from "@/components/Field";
import { getBrowserSupabase } from "@/lib/supabase/browser";

export function ResetForm({ initialEmail }: { initialEmail: string }) {
  const router = useRouter();
  const [email, setEmail] = useState(initialEmail); const [busy, setBusy] = useState(false);
  const ok = /.+@.+\..+/.test(email) && !busy;
  async function submit(e: FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true);
    await getBrowserSupabase().auth.resetPasswordForEmail(email, { redirectTo: `${location.origin}/auth/confirm?next=${encodeURIComponent("/reset/new")}` });
    // 존재하지 않는 이메일도 같은 화면으로(열거 방지)
    router.push(`/signup/sent?kind=recovery&email=${encodeURIComponent(email)}`);
  }
  return (
    <form onSubmit={submit} noValidate>
      <p className="mb-[18px] border-l-2 border-orange pl-2.5 text-[13.5px] leading-[1.6] text-ink-g">가입한 이메일로 재설정 링크를 보냅니다.</p>
      <TextField label="이메일" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Btn variant="dark" type="submit" disabled={!ok} className="mt-4 h-[46px] w-full text-[15px]">재설정 링크 받기</Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><Link href="/login" className="u-link text-ink">로그인</Link></div>
    </form>
  );
}
