import type { Metadata } from "next";
import { Narrow } from "@/components/Narrow";
import { safeNext } from "@/lib/safe-next";
import { ResendButton } from "./ResendButton";

export const metadata: Metadata = { title: "회원가입 | 조달핏", robots: { index: false, follow: false } };

export default async function SentPage({ searchParams }: { searchParams: Promise<{ email?: string; next?: string; kind?: string }> }) {
  const p = await searchParams; const email = p.email ?? ""; const next = safeNext(p.next);
  const recovery = p.kind === "recovery";
  return (
    <Narrow title={recovery ? "비밀번호 재설정" : "회원가입"}>
      <h2 className="m-0 mb-2 text-[20px] font-semibold tracking-[-0.02em]">{recovery ? "재설정 링크를 보냈습니다" : "확인 메일을 보냈습니다"}</h2>
      <p className="m-0 text-[14.5px] leading-[1.65] text-ink-body">{recovery ? "메일의 링크를 열면 새 비밀번호를 정합니다." : "메일의 링크를 열면 가입이 완료됩니다."}</p>
      <ul className="m-0 mt-[18px] list-none p-0 text-[14px] leading-[1.6]">
        <li className="grid grid-cols-[72px_1fr] gap-3 border-t border-rule py-2 max-sm:grid-cols-1"><span className="t-k pt-[3px]">받는 곳</span><b className="border-b-2 border-orange font-semibold">{email || "—"}</b></li>
        <li className="grid grid-cols-[72px_1fr] gap-3 border-t border-rule py-2 max-sm:grid-cols-1"><span className="t-k pt-[3px]">유효</span><span>60분 · 1회</span></li>
        <li className="grid grid-cols-[72px_1fr] gap-3 border-t border-rule py-2 max-sm:grid-cols-1"><span className="t-k pt-[3px]">안 오면</span><span>스팸함 확인 · 보낸 주소 <b className="font-semibold">noreply@jodalfit.co.kr</b></span></li>
      </ul>
      <div className="mt-[18px] flex flex-wrap items-center gap-4 text-[13.5px]">
        {email && <ResendButton email={email} next={next} kind={recovery ? "recovery" : "signup"} />}
        <a href={recovery ? "/reset" : `/signup?next=${encodeURIComponent(next)}`} className="u-link text-ink">다른 이메일</a>
      </div>
    </Narrow>
  );
}
