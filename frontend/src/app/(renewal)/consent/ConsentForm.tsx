"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Btn } from "@/components/Btn";
import { Consent, NO_CONSENT, requiredConsented, type ConsentValue } from "@/components/Consent";

export function ConsentForm({ next }: { next: string }) {
  const router = useRouter();
  const [consent, setConsent] = useState<ConsentValue>(NO_CONSENT);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(false);
  const ok = requiredConsented(consent) && !busy;

  async function submit(e: FormEvent) {
    e.preventDefault(); if (!ok) return; setBusy(true); setErr(false);
    try {
      const r = await fetch("/api/consent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(consent) });
      if (!r.ok) { setErr(true); setBusy(false); return; }
      router.replace(next); router.refresh();
    } catch { setErr(true); setBusy(false); }
  }

  return (
    <form onSubmit={submit} noValidate data-consent-form>
      <Consent value={consent} onChange={setConsent} />
      {err && <p role="alert" className="mb-3 border-l-2 border-orange pl-2.5 text-[13.5px] text-ink">기록하지 못했습니다. 잠시 후 다시</p>}
      <Btn variant="dark" type="submit" disabled={!ok} className="h-[46px] w-full text-[15px]">동의하고 계속</Btn>
      <div className="mt-[18px] flex justify-end border-t border-rule pt-4 text-[14px]"><a href="/logout" data-consent-decline className="u-link text-ink-g">동의하지 않음 · 로그아웃</a></div>
    </form>
  );
}
