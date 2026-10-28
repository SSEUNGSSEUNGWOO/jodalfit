// frontend/src/components/entry/EntrySearch.tsx
// 입구의 묻는 줄 + 검색창 + 안내 줄. 검색 기준(회사 / 키워드)을 고르면 묻는 줄과 안내 줄이 같이 바뀐다 —
// 키워드 기준에서 "어느 회사의 공고를 찾습니까"가 남아 있으면 무엇을 입력하라는지 다시 헷갈린다(2026-10-24).
"use client";

import { useState } from "react";
import { SearchSuggest, type SearchMode } from "./SearchSuggest";

const COPY: Record<SearchMode, { pre: string; key: string; post: string; note: string }> = {
  company: { pre: "어느 ", key: "회사", post: "의 공고를 찾습니까", note: "회사의 등록업종·공급물품·수주 이력 기준으로 선별합니다" },
  keywords: { pre: "어떤 ", key: "업종·품목", post: "의 공고를 찾습니까", note: "입력한 말과 의미가 가까운 공고를 찾습니다 · 참가 자격은 회사로 찾을 때만 판정합니다" },
};

export function EntrySearch() {
  const [mode, setMode] = useState<SearchMode>("company");
  const c = COPY[mode];
  return (
    <>
      <h1 className="mx-auto mt-3 max-w-[760px] text-[26px] font-[650] leading-[1.35] tracking-[-0.03em] text-ink max-sm:text-[20px]">
        {c.pre}<span className="border-b-2 border-orange pb-0.5">{c.key}</span>{c.post}
      </h1>
      <div className="mx-auto mt-[18px] max-w-[760px]">
        <SearchSuggest autoFocus onModeChange={setMode} />
      </div>
      <div className="mx-auto mt-[11px] flex max-w-[760px] items-start gap-x-4 gap-y-1.5 max-sm:flex-col">
        <p className="min-w-0 flex-1 text-[13.5px] text-ink-g">{c.note}</p>
        <a href="https://www.g2b.go.kr/" target="_blank" rel="noopener noreferrer"
          aria-label="나라장터 바로가기 (새 탭)" data-g2b-shortcut
          className="ml-auto shrink-0 border-b border-field text-[13px] text-ink-g transition-colors hover:border-orange hover:text-ink">
          나라장터 바로가기 <span aria-hidden="true">↗</span>
        </a>
      </div>
    </>
  );
}
