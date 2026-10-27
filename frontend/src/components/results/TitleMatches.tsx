// frontend/src/components/results/TitleMatches.tsx
// 키워드 모드 첫 판 — 제목에 검색어가 든 진행 공고 전부(마감 가까운 순). 순위가 아니라 찾기라 게이트 없이 다 보이고,
// 25건씩 쪽을 넘긴다(admin/PagedTable 과 같은 모양). 의미 유사 20건은 이 아래 ResultRows 가 "그 밖에" 로 잇는다. 2026-10-27.
"use client";

import { useState } from "react";
import { Btn } from "@/components/Btn";
import { ReviewButton } from "@/components/ReviewButton";
import { SheetExpand, SheetHead, SheetRow } from "@/components/Sheet";
import { dLeft, won } from "@/lib/format";
import { emitNoticeEvent } from "@/lib/events";
import type { TitleMatch } from "@/types/recommendations";

const PAGE = 25;
const PAGER_BTN = "cursor-pointer border-b border-field text-ink disabled:cursor-default disabled:border-transparent disabled:text-ink-mute";

export function TitleMatches({ rows, terms, capped, loggedIn, reviewed, next, today }: {
  rows: TitleMatch[]; terms: string[]; capped: boolean; loggedIn: boolean; reviewed: Set<string>; next: string; today: Date;
}) {
  const [page, setPage] = useState(0);
  const [rv, setRv] = useState(reviewed);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const cur = Math.min(page, pages - 1);
  const from = cur * PAGE;
  const slice = rows.slice(from, from + PAGE);
  return (
    <section data-title-matches data-page={cur + 1} data-pages={pages}>
      <div className="flex flex-wrap items-start justify-between gap-x-5 gap-y-3 border-b border-ink pb-5 max-sm:pb-4">
        <div>
          <h2 className="text-[24px] font-semibold tracking-[-0.035em] text-ink max-sm:text-[21px]">제목 일치 <span className="num">{rows.length}</span><span className="ml-0.5 text-[16px] font-medium">건</span>{capped && <span className="ml-1.5 text-[14px] font-medium text-ink-g">이상</span>}</h2>
          <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink-g">
            <span>{terms.map((t) => `‘${t}’`).join(" · ")} {terms.length > 1 ? "모두 포함" : "포함"}</span>
            <span>마감 가까운 순</span>
            {capped && <span data-capped>마감 가까운 {rows.length}건만 · 낱말을 더 적어 좁힐 수 있습니다</span>}
          </p>
        </div>
      </div>
      <SheetHead cols={["#", "공고 · 발주기관", "마감", "추정가", ""]} />
      {slice.map((b, i) => {
        const key = `${b.bid_ntce_no}-${b.bid_ntce_ord}`;
        const org = b.dmnd_instt_nm || b.ntce_instt_nm || "—";
        const ev = { bid_ntce_no: b.bid_ntce_no, bid_ntce_ord: b.bid_ntce_ord, rank_position: from + i + 1, algorithm_version: "title" };
        return (
          <SheetRow key={key} no={from + i + 1} title={b.bid_ntce_nm} org={org} dLeft={dLeft(b.bid_clse_date, today)} price={won(b.presmpt_prce)}
            reviewed={rv.has(key)} href={`/notices/${b.bid_ntce_no}`} expandLabel="원문·검토" onOpen={() => emitNoticeEvent({ event_type: "click", ...ev })}>
            <SheetExpand quals={[]} whys={[]} actions={<>
              {b.bid_ntce_url && <Btn variant="dark" href={b.bid_ntce_url} target="_blank" rel="noopener">나라장터 원문</Btn>}
              <ReviewButton no={b.bid_ntce_no} ord={b.bid_ntce_ord} reviewed={rv.has(key)} loggedIn={loggedIn} next={next}
                onChange={(on) => { setRv((s) => { const n = new Set(s); if (on) n.add(key); else n.delete(key); return n; }); if (on) emitNoticeEvent({ event_type: "save", ...ev }); }} />
            </>} />
          </SheetRow>
        );
      })}
      {pages > 1 && (
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[13px] text-ink-g" data-pager>
          <span className="num">{from + 1}–{from + slice.length} / {rows.length}</span>
          <span className="flex-1" />
          <button type="button" disabled={cur === 0} onClick={() => setPage(cur - 1)} className={PAGER_BTN}>이전</button>
          {Array.from({ length: pages }, (_, i) => (
            <button key={i} type="button" onClick={() => setPage(i)} aria-current={i === cur ? "page" : undefined}
              className={`num cursor-pointer px-1 ${i === cur ? "font-[650] text-ink" : "text-ink-g hover:text-ink"}`}>{i + 1}</button>
          ))}
          <button type="button" disabled={cur === pages - 1} onClick={() => setPage(cur + 1)} className={PAGER_BTN}>다음</button>
        </div>
      )}
    </section>
  );
}
