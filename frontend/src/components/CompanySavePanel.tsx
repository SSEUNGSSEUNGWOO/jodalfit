// frontend/src/components/CompanySavePanel.tsx
// 가입 직후 "우리 회사 저장" 칸 — /welcome 과 /consent 가 같은 부품을 쓴다(2026-11-09).
//
// 왜 바꿨나: 저장은 가입 직후 이 화면에서만 일어났다(회원 35명 중 저장 13명, 그중 11명이 가입 1분 안. 뒤에 다시 와서 저장한 사람 0명).
// 그런데 가입 버튼이 눌린 결과 화면의 회사(next 의 company=)를 알면서 빈 검색창을 내밀었다. 이제 그 회사를 체크 하나로 저장한다 —
// 기본은 체크된 상태(본인 검토함에 넣는 일이라 마케팅 동의와 다르다). 알림 메일 동의는 저장 줄 바로 아래 둔다(35명 중 8명만 켰고 저장과 겹치는
// 사람은 2명 — 약관 밑에 떨어져 있어 맥락이 없었다). 광고성 수신동의라 이쪽은 미리 체크하지 않는다.
//
// 저장 자체는 부모가 버튼에서 한다(동의 버튼·시작 버튼과 한 번에). 검색으로 고른 회사는 SaveCompanyForm 이 그 자리에서 저장하고 "저장됨"을 보인다.
"use client";

import { useState } from "react";
import { MarketingRow } from "@/components/Consent";
import { SaveCompanyForm } from "@/components/SaveCompanyForm";

export type SuggestedCompany = { bizrnoNorm: string; name: string };

export function CompanySavePanel({ suggested, save, onSaveChange, savedName, onSavedBySearch, marketing, onMarketingChange, from, idPrefix, title, className }: {
  suggested: SuggestedCompany | null; // next 에서 읽은 "방금 조회한 회사" — 없으면 검색창
  save: boolean; onSaveChange: (v: boolean) => void; // 추정 회사를 저장할지(체크)
  savedName: string | null; onSavedBySearch: (name: string) => void; // 검색창으로 이미 저장한 회사
  marketing: boolean; onMarketingChange: (v: boolean) => void;
  from: "welcome" | "consent"; idPrefix: string;
  title?: string; className?: string;
}) {
  const [useSearch, setUseSearch] = useState(false);
  const showSuggested = !!suggested && !useSearch && !savedName;
  return (
    <section data-save-panel data-suggested={suggested ? "1" : "0"} className={className}>
      {title && <h2 className="m-0 mb-3 text-[14.5px] font-semibold text-ink">{title}</h2>}
      {showSuggested ? (
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <label htmlFor={`${idPrefix}-save`} className="flex cursor-pointer items-start gap-2 text-[14px] leading-[1.55] text-ink">
            <input id={`${idPrefix}-save`} type="checkbox" className="mt-[3px] accent-ink" checked={save} onChange={(e) => onSaveChange(e.target.checked)} data-save-suggested />
            <span>방금 조회한 <b className="font-semibold">{suggested.name}</b> 저장</span>
          </label>
          <button type="button" onClick={() => { setUseSearch(true); onSaveChange(false); }} data-save-other
            className="cursor-pointer border-b border-field text-[13px] text-ink-g hover:border-orange">다른 회사</button>
        </div>
      ) : (
        <SaveCompanyForm from={from} onSaved={onSavedBySearch} />
      )}
      <div className="mt-3">
        <MarketingRow checked={marketing} onChange={onMarketingChange} idPrefix={idPrefix} label="저장한 회사에 새 공고가 있는 주, 월요일 아침 메일 한 통" />
      </div>
    </section>
  );
}
