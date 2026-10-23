"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Btn } from "@/components/Btn";
import { PasswordField, TextField } from "@/components/Field";
import { getBrowserSupabase } from "@/lib/supabase/browser";

const MSG: Record<string, string> = {
  invalid_credentials: "이메일 또는 비밀번호가 맞지 않습니다",
  email_not_confirmed: "이메일 확인 전입니다. 메일의 링크를 열면 로그인됩니다",
};

export function LoginForm({ next, linkError }: { next: string; linkError?: boolean }) {
  const router = useRouter();
  const [email, setEmail] = useState(""); const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null);
  const ok = /.+@.+\..+/.test(email) && pw.length > 0 && !busy;

  async function submit(e: FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true); setErr(null);
    const { error } = await getBrowserSupabase().auth.signInWithPassword({ email, password: pw });
    if (error) { setErr(MSG[error.code ?? ""] ?? "로그인하지 못했습니다. 잠시 후 다시"); setBusy(false); return; }
    router.replace(next); router.refresh();
  }

  return (
    <form onSubmit={submit} noValidate>
      {linkError && <p className="mb-4 border-l-2 border-orange pl-2.5 text-[13.5px] leading-[1.6] text-ink-g"><b className="font-semibold text-ink">링크가 만료되었거나 이미 사용되었습니다.</b> 링크는 60분 동안 한 번만 유효합니다. 가입 확인은 <Link href="/signup" className="u-link text-ink">다시 가입</Link>, 비밀번호는 <Link href="/reset" className="u-link text-ink">재설정</Link>.</p>}
      <TextField label="이메일" type="email" autoComplete="email" inputMode="email" placeholder="you@company.co.kr" value={email} onChange={(e) => setEmail(e.target.value)} />
      <PasswordField className="mt-3.5" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" placeholder="비밀번호" showMinHint={false}
        right={<Link href={`/reset${email ? `?email=${encodeURIComponent(email)}` : ""}`} className="u-link text-[12.5px] text-ink-g">비밀번호 찾기</Link>} />
      {err && <p role="alert" className="mt-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">{err}</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="mt-4 h-[46px] w-full text-[15px]">로그인</Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><Link href={`/signup?next=${encodeURIComponent(next)}`} className="u-link text-ink">회원가입</Link></div>
      <div className="mt-[22px] border-t border-rule pt-4">
        <span className="t-k mb-2 block">로그인하면</span>
        <ul className="m-0 list-none p-0 text-[14px] leading-[1.6]">
          <li className="grid grid-cols-[96px_1fr] gap-3 border-b border-rule-2 py-[5px] max-sm:grid-cols-1 max-sm:gap-0.5"><b className="font-semibold">결과 전부</b><span>상위 5건 뒤의 나머지 공고</span></li>
          <li className="grid grid-cols-[96px_1fr] gap-3 border-b border-rule-2 py-[5px] max-sm:grid-cols-1 max-sm:gap-0.5"><b className="font-semibold">검토함</b><span>검토 표시한 공고 보관</span></li>
          <li className="grid grid-cols-[96px_1fr] gap-3 border-b border-rule-2 py-[5px] max-sm:grid-cols-1 max-sm:gap-0.5"><b className="font-semibold">저장한 회사</b><span>여러 회사 저장, 바로 결과</span></li>
        </ul>
      </div>
    </form>
  );
}
