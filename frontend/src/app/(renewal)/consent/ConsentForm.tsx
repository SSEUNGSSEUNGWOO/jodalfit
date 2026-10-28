"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Btn } from "@/components/Btn";
import { Consent, NO_CONSENT, requiredConsented, type ConsentValue } from "@/components/Consent";
import { SaveCompanyForm } from "@/components/SaveCompanyForm";

/** 소셜 가입 마무리 한 판 — 동의(필수 둘·선택 하나) + 우리 회사 저장(선택)을 한 화면에(승우님 2026-10-28, 두 화면을 거치지 않게).
 *  검색창이 자체 <form> 이라 바깥을 form 으로 감싸지 않는다 — 제출은 버튼 onClick. 회사 저장은 고르는 순간 saved_companies 에 들어가고, 동의는 버튼에서 기록한다. */
export function ConsentForm({ next, showCompany }: { next: string; showCompany: boolean }) {
  const router = useRouter();
  const [consent, setConsent] = useState<ConsentValue>(NO_CONSENT);
  const [savedName, setSavedName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(false);
  const ok = requiredConsented(consent) && !busy;

  async function submit() {
    if (!ok) return; setBusy(true); setErr(false);
    try {
      const r = await fetch("/api/consent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(consent) });
      if (!r.ok) { setErr(true); setBusy(false); return; }
      router.replace(next); router.refresh();
    } catch { setErr(true); setBusy(false); }
  }

  return (
    <div data-consent-form>
      <Consent value={consent} onChange={setConsent} />
      {showCompany && (
        <section className="mb-5 border-t border-rule pt-4">
          <h2 className="m-0 text-[14.5px] font-semibold text-ink"><span className="t-k mr-1.5">[선택]</span>우리 회사 저장</h2>
          <p className="m-0 mb-3 mt-1 text-[13px] leading-[1.6] text-ink-g">
            저장해 두면 검토함에 회사별 추천이 모이고, 알림 메일에 동의한 경우 새 공고가 있는 주에 월요일 아침 한 통을 보냅니다. 나중에 검토함에서도 저장합니다.
          </p>
          <SaveCompanyForm from="consent" onSaved={setSavedName} />
        </section>
      )}
      {err && <p role="alert" className="mb-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">기록하지 못했습니다. 잠시 후 다시</p>}
      <Btn variant="dark" type="button" onClick={submit} disabled={!ok} data-consent-submit className="h-[46px] w-full text-[15px]">
        {savedName ? "동의하고 시작" : "동의하고 계속"}
      </Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><a href="/logout" data-consent-decline className="u-link text-ink-g">동의하지 않음 · 로그아웃</a></div>
    </div>
  );
}
