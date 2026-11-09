"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Btn } from "@/components/Btn";
import { CompanySavePanel, type SuggestedCompany } from "@/components/CompanySavePanel";
import { Consent, NO_CONSENT, requiredConsented, type ConsentValue } from "@/components/Consent";
import { track } from "@/lib/analytics";

/** 소셜 가입 마무리 한 판 — 동의(필수 둘·선택 하나) + 우리 회사 저장(선택)을 한 화면에(승우님 2026-10-28, 두 화면을 거치지 않게).
 *  검색창이 자체 <form> 이라 바깥을 form 으로 감싸지 않는다 — 제출은 버튼 onClick.
 *  방금 조회한 회사(suggested)는 체크된 채로 와서 "동의하고 시작" 버튼이 동의 기록과 저장을 한 번에 한다(2026-11-09).
 *  검색창으로 고른 회사는 고르는 순간 saved_companies 에 들어간다. 알림 메일 동의는 회사 칸 안의 행이 받는다(Consent 의 행은 숨김). */
export function ConsentForm({ next, showCompany, suggested }: { next: string; showCompany: boolean; suggested: SuggestedCompany | null }) {
  const router = useRouter();
  const [consent, setConsent] = useState<ConsentValue>(NO_CONSENT);
  const [save, setSave] = useState(!!suggested);
  const [savedName, setSavedName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(false);
  const ok = requiredConsented(consent) && !busy;
  const willSave = !!savedName || (!!suggested && save);
  useEffect(() => { track("consent_view", { suggested: suggested ? 1 : 0 }); }, [suggested]);

  async function submit() {
    if (!ok) return; setBusy(true); setErr(false);
    try {
      const r = await fetch("/api/consent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(consent) });
      if (!r.ok) { setErr(true); setBusy(false); return; }
      if (showCompany && suggested && save && !savedName) {
        // 동의는 이미 기록됐으므로 저장이 실패해도 멈추지 않는다 — 검토함 빈 상태에서 다시 저장할 수 있다.
        const s = await fetch("/api/saved/companies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nm: suggested.bizrnoNorm }) });
        if (s.ok) track("company_save", { from: "consent", suggested: 1 });
      }
      router.replace(next); router.refresh();
    } catch { setErr(true); setBusy(false); }
  }

  return (
    <div data-consent-form>
      <Consent value={consent} onChange={setConsent} hideMarketing={showCompany} />
      {showCompany && (
        <CompanySavePanel suggested={suggested} save={save} onSaveChange={setSave} savedName={savedName} onSavedBySearch={setSavedName}
          marketing={consent.marketing} onMarketingChange={(m) => setConsent({ ...consent, marketing: m })}
          from="consent" idPrefix="consent" title="우리 회사 저장" className="mb-5 border-t border-rule pt-4" />
      )}
      {err && <p role="alert" className="mb-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">기록하지 못했습니다. 잠시 후 다시</p>}
      <Btn variant="dark" type="button" onClick={submit} disabled={!ok} data-consent-submit className="h-[46px] w-full text-[15px]">
        {willSave ? "동의하고 시작" : "동의하고 계속"}
      </Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><a href="/logout" data-consent-decline className="u-link text-ink-g">동의하지 않음 · 로그아웃</a></div>
    </div>
  );
}
