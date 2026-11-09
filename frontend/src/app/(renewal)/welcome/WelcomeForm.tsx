"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Btn } from "@/components/Btn";
import { CompanySavePanel, type SuggestedCompany } from "@/components/CompanySavePanel";
import { track } from "@/lib/analytics";

/** 환영 화면의 저장 칸 + 버튼(2026-11-09). 방금 조회한 회사는 체크된 채로 와서 "저장하고 계속" 한 번에 끝난다.
 *  검색으로 고른 회사는 SaveCompanyForm 이 그 자리에서 저장한다. 메일 체크가 가입 폼 값과 달라졌으면 /api/consent/marketing 에 반영한다. */
export function WelcomeForm({ next, suggested, marketingOn }: { next: string; suggested: SuggestedCompany | null; marketingOn: boolean }) {
  const router = useRouter();
  const [save, setSave] = useState(!!suggested);
  const [savedName, setSavedName] = useState<string | null>(null);
  const [marketing, setMarketing] = useState(marketingOn);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(false);
  const willSave = !!savedName || (!!suggested && save);
  useEffect(() => { track("welcome_view", { suggested: suggested ? 1 : 0 }); }, [suggested]);

  async function go() {
    if (busy) return; setBusy(true); setErr(false);
    try {
      if (suggested && save && !savedName) {
        const s = await fetch("/api/saved/companies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nm: suggested.bizrnoNorm }) });
        if (!s.ok) { setErr(true); setBusy(false); return; }
        track("company_save", { from: "welcome", suggested: 1 });
      }
      if (marketing !== marketingOn) {
        // 실패해도 진행 — 검토함의 주간 메일 토글에서 다시 바꿀 수 있다.
        await fetch("/api/consent/marketing", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ on: marketing }) }).catch(() => undefined);
      }
      router.push(next); router.refresh();
    } catch { setErr(true); setBusy(false); }
  }

  return (
    <div data-welcome-form>
      <CompanySavePanel suggested={suggested} save={save} onSaveChange={setSave} savedName={savedName} onSavedBySearch={setSavedName}
        marketing={marketing} onMarketingChange={setMarketing} from="welcome" idPrefix="welcome" />
      {err && <p role="alert" className="mb-3 mt-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">저장하지 못했습니다. 잠시 후 다시</p>}
      <Btn variant="dark" type="button" onClick={go} disabled={busy} data-welcome-submit className="mt-4 h-[46px] w-full text-[15px]">
        {willSave ? "저장하고 계속" : "계속"}
      </Btn>
    </div>
  );
}
