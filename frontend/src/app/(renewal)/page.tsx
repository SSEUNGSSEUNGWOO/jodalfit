// frontend/src/app/(renewal)/page.tsx
// 입구(04) — 제품의 정문. 실사용자 검색의 97.7% 가 여기서 시작한다
// (2026-10-23 실측: search_logs source='user' 1,653건 중 / 1,615 · /recommendations 28).
//
// 설명 페이지를 따로 두지 않는다 — 그러면 97.7% 에게 클릭을 하나 더 시킨다.
// 처음 온 사람에게 뭐 하는 곳인지 한 줄로 알리고 바로 아래에 검색창을 둔다.
// 시안: docs/design/prototypes/entry-v2.html 의 D 안 + C 안의 머리 한 줄.
import type { Metadata } from "next";
import { SearchSuggest } from "@/components/entry/SearchSuggest";
import { EntryPanel } from "@/components/entry/EntryPanel";
import { RecentChips } from "@/components/entry/RecentChips";
import { getEntryData } from "@/lib/entry";

export const metadata: Metadata = {
  title: "조달핏 — 우리 회사가 검토할 만한 입찰공고",
  description:
    "회사명이나 사업자등록번호를 넣으면 등록업종·공급물품·수주 이력으로 지금 입찰 가능한 나라장터 공고 중 검토할 만한 것을 추려 드립니다.",
  alternates: { canonical: "/" },
};

export default async function EntryPage() {
  // 판 수치가 실패해도 검색은 되어야 한다 — 읽기가 깨지면 판만 접는다.
  const entry = await getEntryData().catch(() => null);
  return (
    <>
      {/* 머리 한 줄 — 처음 온 사람에게 "여기가 뭐 하는 곳인가"를 답한다. 묻는 줄이 그 아래. */}
      <p className="mx-auto mt-12 max-w-[760px] text-[15px] text-ink-g max-sm:mt-7 max-sm:text-[14px]">
        나라장터 공고 중 <b className="font-[650] text-ink">우리 회사가 검토할 만한 것</b>만 추립니다.
        낙찰을 예측하지 않습니다.
      </p>
      <h1 className="mx-auto mt-3 max-w-[760px] text-[26px] font-[650] leading-[1.35] tracking-[-0.03em] text-ink max-sm:text-[20px]">
        어느 <span className="border-b-2 border-orange pb-0.5">회사</span>의 공고를 찾습니까
      </h1>
      <div className="mx-auto mt-[18px] max-w-[760px]">
        <SearchSuggest autoFocus />
      </div>
      <p className="mx-auto mt-[11px] max-w-[760px] text-[13.5px] text-ink-g">
        회사명 · 사업자등록번호 · 업종 또는 품목 중 아는 것 하나면 됩니다
      </p>
      <RecentChips />
      {entry && <EntryPanel d={entry} />}
    </>
  );
}
