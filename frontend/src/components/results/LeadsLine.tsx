// frontend/src/components/results/LeadsLine.tsx
// 공고 목록 다음의 접히는 줄 — 사전규격(골든타임)과 발주계획.
//
// 왜 공고 목록에 섞지 않나: 추천되는 공고는 이미 본공고라 의견 창이 닫힌 뒤다.
// 2026-10-23 확인 — 활성 공고 10,382건 중 사전규격과 이어지고 의견 접수가 아직 열린 건 53건(0.5%).
// 접수 중 사전규격 2,547건은 아직 공고 번호 자체가 없다. 같은 목록에 둘 수 없으므로 별도 줄이다.
//
// 지금까지는 숫자만 띄우고(공고 20 · 사전규격 4 · 발주계획 18) 누를 데가 없었다 — 목록을 서버가
// 만들어 버렸다. 이 줄이 그 자리를 만든다. 둘 다 0건이면 줄 자체를 그리지 않는다.
"use client";

import { useId, useState } from "react";
import type { OrderPlanRecommendation, PreSpecRecommendation } from "@/types/recommendations";
import { cn } from "@/lib/utils";

const nf = new Intl.NumberFormat("ko-KR");
const KST = "Asia/Seoul";

function won(v: number | null): string {
  if (!v) return "—";
  return v >= 100_000_000 ? `${(v / 100_000_000).toFixed(1)}억` : `${nf.format(Math.round(v / 10_000))}만`;
}

/** 의견 마감 표시. 당일·익일은 시계 시각 — 마감이 23시에 몰려 있어 'D-0' 은 몇 시까지인지를 숨긴다. */
function when(iso: string | null, now: Date): { text: string; hot: boolean } {
  if (!iso) return { text: "—", hot: false };
  const t = new Date(iso);
  if (Number.isNaN(+t)) return { text: "—", hot: false };
  if (+t <= +now) return { text: "마감", hot: false };
  const day = (d: Date) => d.toLocaleDateString("en-CA", { timeZone: KST });
  const hhmm = t.toLocaleTimeString("ko-KR", { timeZone: KST, hour: "2-digit", minute: "2-digit", hour12: false });
  const days = Math.round((Date.parse(`${day(t)}T00:00:00+09:00`) - Date.parse(`${day(now)}T00:00:00+09:00`)) / 86400_000);
  if (days <= 0) return { text: `오늘 ${hhmm}`, hot: true };
  if (days === 1) return { text: `내일 ${hhmm}`, hot: true };
  return { text: `D-${days}`, hot: days <= 2 };
}

/** 의견 창이 아직 열린 사전규격만 "골든타임" 이다 — 마감 지난 행은 세지 않는다. */
function isLive(p: PreSpecRecommendation, now: Date): boolean {
  const t = p.opnin_rgst_clse_dt ? new Date(p.opnin_rgst_clse_dt) : null;
  return !!t && !Number.isNaN(+t) && +t > +now;
}

export function LeadsLine({ preSpecs, orderPlans }: { preSpecs: PreSpecRecommendation[]; orderPlans: OrderPlanRecommendation[] }) {
  const now = new Date();
  const live = preSpecs.filter((p) => isLive(p, now)).length;
  const [preOpen, setPreOpen] = useState(live > 0);
  const [planOpen, setPlanOpen] = useState(true);
  const [allPlans, setAllPlans] = useState(false);
  const preId = useId();
  const planId = useId();
  if (!preSpecs.length && !orderPlans.length) return null;

  const soon = preSpecs.filter((p) => when(p.opnin_rgst_clse_dt, now).hot).length;
  const plans = allPlans ? orderPlans : orderPlans.slice(0, 3);
  const toggleClass = "flex w-full cursor-pointer flex-wrap items-baseline gap-x-3 gap-y-1 text-left";
  return (
    <div data-leads data-golden={live > 0 ? live : undefined} className="mt-6 border-t border-hair pt-5">
      <h3 className="m-0 mb-3 text-[12px] font-semibold text-ink-g">공고 전 단계</h3>
      {preSpecs.length > 0 && (
        <section data-pre-specs>
          <button type="button" onClick={() => setPreOpen((v) => !v)} aria-expanded={preOpen} aria-controls={preId}
            aria-label={`사전규격 ${preOpen ? "접기" : "펼치기"}`} className={toggleClass}>
            <span className="text-[14px] font-[650] text-ink">
              {live > 0 ? <><span className="text-orange-ink">골든타임</span> {nf.format(live)}건</> : <>사전규격 {nf.format(preSpecs.length)}건</>}
            </span>
            {soon > 0 && <span className="text-[12.5px] text-orange-ink">{soon}건 곧 마감</span>}
            <span className="ml-auto border-b border-field text-[13px] text-ink-g">{preOpen ? "접기" : "펼치기"}</span>
          </button>
          <div id={preId} hidden={!preOpen}>
            <p className="mb-0 mt-2 text-[12.5px] leading-[1.7] text-ink-g">사전규격에 의견을 내는 기간입니다. 본공고가 뜨면 사양은 거의 못 바꿉니다.</p>
            <ul className="mt-1.5">
              {preSpecs.map((p) => {
                const w = when(p.opnin_rgst_clse_dt, now);
                return (
                  <li key={p.bf_spec_rgst_no} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-3.5 border-b border-rule-2 py-2 max-sm:grid-cols-[minmax(0,1fr)_auto]">
                    <span className="truncate text-[13.5px]">{p.prdct_clsfc_no_nm || "—"}<span className="ml-2 text-[12px] text-ink-g">{p.rl_dminstt_nm || p.order_instt_nm || "—"}</span></span>
                    <span className={cn("min-w-[88px] text-right text-[13px] font-[650]", w.hot ? "text-orange-ink" : "text-ink")}>{w.text}</span>
                    <span className="num min-w-[62px] text-right text-[13px] text-ink-g max-sm:hidden">{won(p.asign_bdgt_amt)}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      )}
      {orderPlans.length > 0 && (
        <section data-order-plans className={cn(preSpecs.length > 0 && "mt-4 border-t border-hair pt-4")}>
          <button type="button" onClick={() => setPlanOpen((v) => !v)} aria-expanded={planOpen} aria-controls={planId}
            aria-label={`발주계획 ${planOpen ? "접기" : "펼치기"}`} className={toggleClass}>
            <span className="text-[14px] font-[650] text-ink">앞으로 나올 공고 {nf.format(orderPlans.length)}건</span>
            <span className="text-[12.5px] text-ink-g">발주계획</span>
            <span className="ml-auto border-b border-field text-[13px] text-ink-g">{planOpen ? "접기" : "펼치기"}</span>
          </button>
          <div id={planId} hidden={!planOpen}>
            <p className="mb-0 mt-2 text-[12.5px] leading-[1.7] text-ink-g">기관이 발주를 예고한 사업입니다. 사양은 아직 정해지지 않았습니다.</p>
            <ul id={`${planId}-rows`} className="mt-1.5">
              {plans.map((o) => (
                <li key={o.order_plan_unty_no} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-3.5 border-b border-rule-2 py-2 max-sm:grid-cols-[minmax(0,1fr)_auto]">
                  <span className="truncate text-[13.5px]">{o.prdct_clsfc_no_nm || o.biz_nm || "—"}<span className="ml-2 text-[12px] text-ink-g">{o.order_instt_nm || o.totlmng_instt_nm || "—"}</span></span>
                  <span className="min-w-[88px] text-right text-[13px] text-ink-g">{o.order_year && o.order_mnth ? `${o.order_year}.${String(o.order_mnth).padStart(2, "0")} 예정` : "시기 미정"}</span>
                  <span className="num min-w-[62px] text-right text-[13px] text-ink-g max-sm:hidden">{won(o.sum_order_amt)}</span>
                </li>
              ))}
            </ul>
            {orderPlans.length > 3 && <button data-plans-more type="button" onClick={() => setAllPlans((v) => !v)} aria-expanded={allPlans} aria-controls={`${planId}-rows`}
              className="mt-3 cursor-pointer border-b border-field text-[13px] font-medium text-ink-g hover:border-orange">
              {allPlans ? "발주계획 3건만 보기" : `발주계획 ${nf.format(orderPlans.length - 3)}건 더 보기`}
            </button>}
          </div>
        </section>
      )}
    </div>
  );
}
