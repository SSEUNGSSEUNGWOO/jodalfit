// frontend/src/components/Consent.tsx
"use client";

import Link from "next/link";

export type ConsentValue = { terms: boolean; privacy: boolean; marketing: boolean };
export const NO_CONSENT: ConsentValue = { terms: false, privacy: false, marketing: false };
export const requiredConsented = (c: ConsentValue) => c.terms && c.privacy;

const row = "flex cursor-pointer items-start gap-2 text-[13px] leading-[1.55] text-ink-body";
const box = "mt-[3px] accent-ink";

/** 알림 메일(선택) 한 줄 — 가입 동의 묶음 안에, 또는 우리 회사 저장 칸 옆에(CompanySavePanel, 2026-11-09: 저장과 같은 자리에 두어야 맥락이 생긴다).
 *  광고성 정보 수신동의라 미리 체크하지 않는다. */
export function MarketingRow({ checked, onChange, idPrefix = "consent", label = "알림 메일 수신 동의 — 저장한 회사에 새 공고가 있으면 매주 월요일 한 통" }: {
  checked: boolean; onChange: (v: boolean) => void; idPrefix?: string; label?: string;
}) {
  return (
    <label htmlFor={`${idPrefix}-marketing`} className={`${row} text-ink-g`}>
      <input id={`${idPrefix}-marketing`} type="checkbox" className={box} checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span><span className="t-k mr-1.5">[선택]</span>{label}</span>
    </label>
  );
}

/** 가입 동의 — 이용약관(필수) · 개인정보(필수) · 알림 메일(선택). 문구는 시안 gen_login.py::consent.
 *  hideMarketing: 메일 행을 다른 자리(회사 저장 칸)에 그릴 때. */
export function Consent({ value, onChange, idPrefix = "consent", hideMarketing = false }: {
  value: ConsentValue; onChange: (v: ConsentValue) => void; idPrefix?: string; hideMarketing?: boolean;
}) {
  return (
    <div className="my-4 flex flex-col gap-2">
      <label htmlFor={`${idPrefix}-terms`} className={row}>
        <input id={`${idPrefix}-terms`} type="checkbox" className={box} checked={value.terms} onChange={(e) => onChange({ ...value, terms: e.target.checked })} />
        <span><b className="font-semibold">[필수]</b> <Link href="/terms" target="_blank" className="u-link">이용약관</Link> 동의</span>
      </label>
      <label htmlFor={`${idPrefix}-privacy`} className={row}>
        <input id={`${idPrefix}-privacy`} type="checkbox" className={box} checked={value.privacy} onChange={(e) => onChange({ ...value, privacy: e.target.checked })} />
        <span><b className="font-semibold">[필수]</b> 개인정보 수집·이용 동의 — 이메일 주소 · 로그인·검토함·저장한 회사 보관 · 탈퇴 시 삭제. <Link href="/privacy" target="_blank" className="u-link">처리방침</Link></span>
      </label>
      {!hideMarketing && <MarketingRow checked={value.marketing} onChange={(m) => onChange({ ...value, marketing: m })} idPrefix={idPrefix} />}
    </div>
  );
}
