"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Btn } from "@/components/Btn";
import { PasswordField, TextField } from "@/components/Field";
import { getBrowserSupabase } from "@/lib/supabase/browser";

export function NewPasswordForm({ email }: { email: string }) {
  const router = useRouter();
  const [a, setA] = useState(""); const [b, setB] = useState(""); const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const ok = a.length >= 8 && a === b && !busy;
  async function submit(e: FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true); setErr(null);
    const { error } = await getBrowserSupabase().auth.updateUser({ password: a });
    if (error) { setErr(error.code === "same_password" ? "이전과 같은 비밀번호입니다" : "변경하지 못했습니다. 링크를 다시 받기"); setBusy(false); return; }
    router.replace("/recommendations"); router.refresh();
  }
  return (
    <form onSubmit={submit} noValidate>
      <TextField label="계정" type="email" value={email} disabled readOnly />
      <PasswordField className="mt-3.5" label="새 비밀번호" value={a} onChange={(e) => setA(e.target.value)} autoComplete="new-password" placeholder="8자 이상" />
      <PasswordField className="mt-3.5" label="새 비밀번호 확인" value={b} onChange={(e) => setB(e.target.value)} autoComplete="new-password" placeholder="한 번 더" showMinHint={false} />
      {err && <p role="alert" className="mt-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err}</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="mt-4 h-[46px] w-full text-[15px]">변경</Btn>
      <p className="mt-3.5 text-[12.5px] leading-[1.6] text-ink-dim">변경 시 다른 기기 로그인 해제.</p>
    </form>
  );
}
