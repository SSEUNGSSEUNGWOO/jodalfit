// frontend/src/components/Consent.tsx
"use client";

import Link from "next/link";

export type ConsentValue = { terms: boolean; privacy: boolean; marketing: boolean };
export const NO_CONSENT: ConsentValue = { terms: false, privacy: false, marketing: false };
export const requiredConsented = (c: ConsentValue) => c.terms && c.privacy;

/** 가입 동의 — 이용약관(필수) · 개인정보(필수) · 알림 메일(선택). 문구는 시안 gen_login.py::consent. */
export function Consent({ value, onChange, idPrefix = "consent" }: { value: ConsentValue; onChange: (v: ConsentValue) => void; idPrefix?: string }) {
  const row = "flex cursor-pointer items-start gap-2 text-[13px] leading-[1.55] text-ink-body";
  const box = "mt-[3px] accent-ink";
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
      <label htmlFor={`${idPrefix}-marketing`} className={`${row} text-ink-g`}>
        <input id={`${idPrefix}-marketing`} type="checkbox" className={box} checked={value.marketing} onChange={(e) => onChange({ ...value, marketing: e.target.checked })} />
        <span><span className="t-k mr-1.5">[선택]</span>알림 메일 수신 동의 — 저장한 회사에 새 공고가 있으면 매주 월요일 한 통</span>
      </label>
    </div>
  );
}
