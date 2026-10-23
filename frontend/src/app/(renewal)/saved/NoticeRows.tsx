// frontend/src/app/(renewal)/saved/NoticeRows.tsx
// 검토함 공고 표. 격자는 시안 gen_saved.py:34 (제목 / 마감 84 / 추정가 84 / 해제 64), 390 은 제목 / 마감 72 만.
// 해제는 행이 흐려지고 "되돌리기"로 바뀐다 — 즉시 사라지지 않는다(시안). 되돌리기는 같은 값으로 다시 insert.
"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ReviewedNoticeRow } from "@/lib/saved";
import { won } from "@/lib/format";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { cn } from "@/lib/utils";

const GRID = "grid grid-cols-[minmax(0,1fr)_84px_84px_64px] gap-x-3 items-start max-sm:grid-cols-[minmax(0,1fr)_72px]";

function Row({ r, past }: { r: ReviewedNoticeRow; past: boolean }) {
  const router = useRouter();
  const [removed, setRemoved] = useState(false);
  async function toggle() {
    const sb = getBrowserSupabase();
    const next = !removed;
    setRemoved(next);
    const { error } = next
      ? await sb.from("reviewed_notices").delete().eq("bid_ntce_no", r.no).eq("bid_ntce_ord", r.ord)
      : await sb.from("reviewed_notices").insert({ bid_ntce_no: r.no, bid_ntce_ord: r.ord, via_bizrno_norm: r.via?.bizrnoNorm ?? null, why: r.why });
    if (error && error.code !== "23505") { setRemoved(!next); return; }
    router.refresh();
  }
  const hot = !past && !!r.d && r.d.days <= 7;
  return (
    <div data-saved-row className={cn(GRID, "border-b border-rule py-3 transition-opacity duration-300", removed && "opacity-35", past && "text-ink-mute")}>
      <span className="min-w-0">
        <span className={cn("block text-[16px] font-semibold leading-snug", past ? "text-ink-mute" : "text-ink")}>
          <Link href={`/notices/${r.no}`} className="hover:border-b hover:border-orange">{r.title}</Link>
        </span>
        <span className="mt-1 block text-[13.5px] text-ink-dim max-sm:text-[13px]">
          {r.via && (
            <span className={cn("before:mr-1 before:text-[11px] before:content-['★']", past ? "before:text-[#b8b6b0]" : "before:text-orange")}>{r.via.name}</span>
          )}
          {r.via && <span className="mx-[7px] text-[#c9c9c4]">·</span>}
          <span>{r.org}</span>
          {r.why && !past && <span className="ml-[7px] rounded-[4px] border border-hair px-1.5 py-px text-[12px] text-ink-g">{r.why}</span>}
        </span>
      </span>
      <span className={cn("num pt-0.5 text-right text-[15px] font-semibold", hot && "text-orange", past && "font-medium")}>
        {r.d ? (r.d.days < 0 ? "마감" : `D-${r.d.days}`) : "—"}
        {r.d && <small className={cn("block text-[12px] font-normal", past ? "text-[#9b9a95]" : "text-ink-mute")}>{r.d.month}.{String(r.d.day).padStart(2, "0")}</small>}
      </span>
      <span className="num pt-0.5 text-right text-[15px] max-sm:hidden">{won(r.price)}</span>
      <span className="pt-1 text-right text-[13px] max-sm:hidden">
        <button type="button" onClick={toggle} data-unreview className={cn("cursor-pointer border-b", removed ? "border-ink text-ink" : "border-[#d8d6d0] text-ink-g hover:border-orange")}>
          {removed ? "되돌리기" : "해제"}
        </button>
      </span>
    </div>
  );
}

export function NoticeRows({ live, past }: { live: ReviewedNoticeRow[]; past: ReviewedNoticeRow[] }) {
  if (live.length === 0 && past.length === 0) {
    return (
      <div data-saved-empty className="pb-2.5 pt-[30px] text-[14px] leading-[1.7] text-ink-g">
        <b className="mb-1 block text-[16px] font-[650] text-ink">검토 표시한 공고가 없습니다</b>
        결과 표의 행을 펼쳐 검토를 누르면 여기에 보관됩니다.
      </div>
    );
  }
  return (
    <>
      <div className={cn(GRID, "border-b border-ink pb-2 pt-4 text-[12px] text-ink-mute max-sm:hidden")}>
        <span>공고 · 결과를 본 회사 · 발주기관 · 근거</span><span className="text-right">마감</span><span className="text-right">추정가</span><span />
      </div>
      {live.map((r) => <Row key={`${r.no}-${r.ord}`} r={r} past={false} />)}
      {past.length > 0 && (
        <div data-saved-past className="mt-[22px]">
          <span className="block border-b border-hair pb-2 text-[12px] text-ink-mute">마감 지남 {past.length}건 — 마감 30일 뒤 자동 정리</span>
          {past.map((r) => <Row key={`${r.no}-${r.ord}`} r={r} past />)}
        </div>
      )}
    </>
  );
}
