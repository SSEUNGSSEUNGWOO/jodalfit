"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Btn } from "@/components/Btn";
import { Consent, NO_CONSENT, requiredConsented, type ConsentValue } from "@/components/Consent";
import { PasswordField, TextField } from "@/components/Field";
import { PRIVACY_VERSION } from "@/lib/privacy";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { TERMS_VERSION } from "@/lib/terms";

export function SignupForm({ next }: { next: string }) {
  const router = useRouter();
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [consent, setConsent] = useState<ConsentValue>(NO_CONSENT);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const ok = /.+@.+\..+/.test(email) && pw.length >= 8 && requiredConsented(consent) && !busy;

  async function submit(e: FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true); setErr(null);
    const redirectTo = `${location.origin}/auth/confirm?next=${encodeURIComponent(next)}`;
    const { data, error } = await getBrowserSupabase().auth.signUp({
      email, password: pw,
      options: { emailRedirectTo: redirectTo, data: { terms_version: TERMS_VERSION, privacy_version: PRIVACY_VERSION, marketing_opt_in: consent.marketing, consented_at: new Date().toISOString() } },
    });
    if (error) { setErr(error.code === "user_already_exists" ? "이미 가입된 이메일입니다. 로그인 또는 비밀번호 재설정" : "가입하지 못했습니다. 잠시 후 다시"); setBusy(false); return; }
    // Confirm email ON 이면 identities 가 빈 기존 계정에도 성공처럼 돌아온다(열거 방지). 같은 안내로 보낸다.
    void data;
    router.push(`/signup/sent?email=${encodeURIComponent(email)}&next=${encodeURIComponent(next)}`);
  }

  return (
    <form onSubmit={submit} noValidate>
      <TextField label="이메일" type="email" autoComplete="email" inputMode="email" placeholder="you@company.co.kr" value={email} onChange={(e) => setEmail(e.target.value)} hint="확인 메일 발송" />
      <PasswordField className="mt-3.5" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" placeholder="8자 이상" />
      <Consent value={consent} onChange={setConsent} />
      {err && <p role="alert" className="mb-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err}</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="h-[46px] w-full text-[15px]">가입</Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><Link href={`/login?next=${encodeURIComponent(next)}`} className="u-link text-ink">로그인</Link></div>
    </form>
  );
}
