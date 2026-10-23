// frontend/src/app/(renewal)/saved/CompanyRows.tsx
// 검토함 저장한 회사 표. 390 은 회사 / 오늘 아래에 결과·해제 버튼을 둔다.
// "오늘 N건 검토할 공고"는 추천 캐시 기준 — 캐시가 없으면 "—"와 "결과" 링크만.
// 행 토글은 router.refresh() 를 부르지 않는다 — 다시 그리면 삭제된 행이 빠져 "되돌리기" 가 사라진다. 숫자는 다음 이동 때 갱신.
"use client";

import Link from "next/link";
import { useState } from "react";
import type { SavedCompanyRow } from "@/lib/saved";
import { rgnBase } from "@/lib/format";
import { getBrowserSupabase } from "@/lib/supabase/browser";
import { cn } from "@/lib/utils";

const GRID = "grid grid-cols-[minmax(0,1fr)_150px_110px_110px] gap-x-3 items-start max-sm:grid-cols-[minmax(0,1fr)_auto]";

function Row({ c }: { c: SavedCompanyRow }) {
  const [removed, setRemoved] = useState(false);
  const [busy, setBusy] = useState(false);
  async function toggle() {
    if (busy) return;
    const sb = getBrowserSupabase();
    const next = !removed;
    setRemoved(next);
    setBusy(true);
    const { error } = next
      ? await sb.from("saved_companies").delete().eq("bizrno_norm", c.bizrnoNorm)
      : await sb.from("saved_companies").insert({ bizrno_norm: c.bizrnoNorm });
    setBusy(false);
    if (error && error.code !== "23505") { setRemoved(!next); return; }
  }
  const s = c.stats;
  const hot = !!s?.soonest && s.soonest.days <= 7;
  return (
    <div data-saved-company className={cn(GRID, "border-b border-rule py-3.5 transition-opacity duration-300", removed && "opacity-35")}>
      <span className="min-w-0">
        <Link href={`/companies/${c.bizrnoNorm}`} className="block text-[16px] font-semibold text-ink before:mr-1.5 before:text-[13px] before:text-orange-ink before:content-['★'] hover:underline">{c.name}</Link>
        <span className="mt-1 block text-[13.5px] text-ink-dim">
          <span>{rgnBase(c.region) || "—"}</span><span className="mx-[7px] text-[#c9c9c4]">·</span><span>등록업종 {c.industries}</span>
        </span>
      </span>
      <span className="num pt-0.5 text-[14px] text-ink-dim">
        {s ? <><b className="text-[15px] font-semibold text-ink max-sm:text-[16px]">{s.total}건</b> 검토할 공고</> : <span className="text-ink-mute">— 결과 없음</span>}
        {s && <small className="block text-[12px] text-ink-mute">이번 주 마감 {s.week}건</small>}
      </span>
      <span className="num pt-0.5 text-[14px] max-sm:hidden">
        {s?.soonest ? (
          <><span className={cn("text-[15px] font-semibold", hot ? "text-orange-ink" : "text-ink")}>D-{s.soonest.days}</span>
            <small className="block text-[12px] text-ink-mute">가장 빠른 마감 {s.soonest.month}.{String(s.soonest.day).padStart(2, "0")}</small></>
        ) : <span className="text-ink-mute">—</span>}
      </span>
      <span className="flex items-center justify-end gap-3 pt-0.5 text-[13px] max-sm:col-span-full max-sm:pt-3">
        <Link href={`/companies/${c.bizrnoNorm}`} className="border-b border-[#e3e1dc] text-ink hover:border-orange">결과</Link>
        <button type="button" onClick={toggle} disabled={busy} data-unstar className={cn("cursor-pointer border-b", removed ? "border-ink text-ink" : "border-[#d8d6d0] text-ink-g hover:border-orange")}>
          {removed ? "되돌리기" : "★ 해제"}
        </button>
      </span>
    </div>
  );
}

export function CompanyRows({ rows }: { rows: SavedCompanyRow[] }) {
  if (rows.length === 0) {
    return (
      <div data-saved-empty className="pb-2.5 pt-[30px] text-[14px] leading-[1.7] text-ink-g">
        <b className="mb-1 block text-[16px] font-[650] text-ink">저장한 회사가 없습니다</b>
        회사 페이지 또는 결과 머리의 ☆ 로 저장합니다.
      </div>
    );
  }
  return (
    <>
      <div className={cn(GRID, "border-b border-ink pb-2 pt-4 text-[12px] text-ink-mute max-sm:hidden")}>
        <span>회사</span><span>오늘</span><span>마감</span><span />
      </div>
      {rows.map((c) => <Row key={c.bizrnoNorm} c={c} />)}
    </>
  );
}
