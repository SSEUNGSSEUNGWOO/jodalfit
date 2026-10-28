// frontend/src/components/results/ResultRows.tsx
// 오른쪽 단 — 표 5건 + Gate + 흐림 미리보기 1건(로그인이면 전부).
"use client";

import { useState } from "react";
import { Gate } from "@/components/Gate";
import { Btn } from "@/components/Btn";
import { ReviewButton } from "@/components/ReviewButton";
import { SheetExpand, SheetFade, SheetHead, SheetRow } from "@/components/Sheet";
import { dLeft, won } from "@/lib/format";
import { emitNoticeEvent } from "@/lib/events";
import { strongestWhy } from "@/lib/saved-stats";
import { qualLines, whyLines } from "@/lib/why";
import type { BidRecommendation } from "@/types/recommendations";

const FREE = 5;

export function ResultRows({ results, loggedIn, reviewed, viaBizrno, next, today, keywordMode = false }: {
  results: BidRecommendation[]; loggedIn: boolean; reviewed: Set<string>; viaBizrno: string | null; next: string; today: Date; keywordMode?: boolean;
}) {
  const [rv, setRv] = useState(reviewed);
  const row = (b: BidRecommendation, i: number) => {
    const key = `${b.bid_ntce_no}-${b.bid_ntce_ord}`;
    const org = b.dmnd_instt_nm || b.ntce_instt_nm || "—";
    const why = keywordMode ? null : strongestWhy(b.score_breakdown);
    const ev = { bid_ntce_no: b.bid_ntce_no, bid_ntce_ord: b.bid_ntce_ord, target_bizrno: viaBizrno, rank_position: i + 1, algorithm_version: "v2", score: b.score };
    return (
      <SheetRow key={key} no={i + 1} title={b.bid_ntce_nm} org={org} why={why ?? undefined} dLeft={dLeft(b.bid_clse_date, today)} price={won(b.presmpt_prce)}
        reviewed={rv.has(key)} href={`/notices/${b.bid_ntce_no}`} expandLabel={keywordMode ? "원문·검토" : undefined}
        onVisit={() => emitNoticeEvent({ event_type: "click", ...ev })}
        onOpen={() => emitNoticeEvent({ event_type: "click", ...ev })}
        action={<ReviewButton no={b.bid_ntce_no} ord={b.bid_ntce_ord} via={viaBizrno} why={why} reviewed={rv.has(key)} loggedIn={loggedIn} next={next}
          rank={i + 1} score={b.score} algorithm="v2" label="저장" activeLabel="저장됨"
          onChange={(on) => setRv((s) => { const n = new Set(s); if (on) n.add(key); else n.delete(key); return n; })} />}>
        <SheetExpand quals={keywordMode ? [] : qualLines(b.qualification)} whys={keywordMode ? [] : whyLines(b.score_breakdown, org)}
          actions={<>
            {b.bid_ntce_url && <Btn variant="dark" href={b.bid_ntce_url} target="_blank" rel="noopener">나라장터 원문</Btn>}
          </>} />
      </SheetRow>
    );
  };
  const head = results.slice(0, loggedIn ? results.length : FREE);
  const rest = loggedIn ? [] : results.slice(FREE);
  return (
    <div data-rows>
      <SheetHead />
      {head.map(row)}
      {rest.length > 0 && <Gate rest={rest.length} next={next} />}
      {rest.length > 0 && <SheetFade>{rest.slice(0, 1).map((b, i) => row(b, i + FREE))}</SheetFade>}
    </div>
  );
}

export function ZeroBlock({ reason, viaBizrno }: { reason: "qualify" | "rank"; viaBizrno: string | null }) {
  return (
    <div data-zero className="pb-[34px] pt-[22px]">
      <b className="block text-[18px] font-[650] tracking-[-0.015em] text-ink">{reason === "qualify" ? "참가 자격이 있는 공고가 없습니다" : "검토할 공고가 없습니다"}</b>
      <span className="mt-1.5 block text-[14px] text-ink-dim">기준 확인 또는 키워드 검색</span>
      <div className="mt-[18px] flex flex-wrap items-center gap-2.5">
        <Btn variant="dark" href="/recommendations">키워드로 공고 검색</Btn>
        {viaBizrno && <Btn href="/privacy#request">업종·물품 수정 요청</Btn>}
      </div>
    </div>
  );
}
