// frontend/src/components/results/FunnelLine.tsx
// 걸러낸 경로(숫자 + 단계 라벨) 왼쪽, 종류 탭·마감 요약 오른쪽. 장면이 접힌 뒤(open) 펼쳐진다. 0건이면 탭·마감 요약 숨김(12건 기준 계산이라 거짓).
import { cn } from "@/lib/utils";
import { FUNNEL_LABELS, type SceneCounts } from "./Scene";

const fmt = (n: number | null) => (n == null ? "…" : n.toLocaleString("ko-KR"));

export function FunnelLine({ counts, open, tabs, due }: {
  counts: SceneCounts; open: boolean;
  tabs: { notices: number; preSpecs: number; orderPlans: number } | null;
  due: { week: number; soonest: { days: number; month: number; day: number } | null } | null;
}) {
  const nums = [counts.total, counts.candidates, counts.passed, counts.results];
  return (
    <div data-funnel className={cn("grid grid-cols-[1fr_auto] items-start gap-6 overflow-hidden transition-[grid-template-rows,padding,opacity] duration-[450ms] [transition-timing-function:var(--ease-sheet)] max-sm:grid-cols-1 max-sm:gap-y-2.5", open ? "grid-rows-[1fr] pt-4 opacity-100" : "grid-rows-[0fr] opacity-0")}>
      <div className="flex min-h-0 items-start gap-3 overflow-hidden">
        <span className="t-k pt-[3px] max-sm:hidden">걸러낸 경로</span>
        {FUNNEL_LABELS.map((l, i) => (
          <div key={l} className="contents">
            {i > 0 && <i className="pt-0.5 text-[16px] not-italic text-ink-mute">→</i>}
            <div className="flex flex-col">
              <span className="num flex items-baseline">
                <b className={cn("text-[28px] leading-[1.15] max-sm:text-[20px]", i === 3 && "text-[34px] text-orange max-sm:text-[24px]")} data-n={i}>{fmt(nums[i])}</b>
                {i === 3 && <span className="ml-1 text-[11.5px] text-ink-mute">건</span>}
              </span>
              <span className="mt-[3px] text-[12.5px] leading-[1.3] text-ink-mute max-sm:text-[10.5px]">{l}</span>
            </div>
          </div>
        ))}
      </div>
      {tabs && due && (
        <div className="min-h-0 overflow-hidden text-right text-[14px] leading-[1.9] text-ink-g max-sm:text-left" data-tabs>
          <div>
            <em className="border-b border-ink pb-px font-[650] not-italic text-ink">공고 {tabs.notices}</em>
            <span className="before:mx-2 before:text-[#c9c9c4] before:content-['·']">사전규격 {tabs.preSpecs}</span>
            <span className="before:mx-2 before:text-[#c9c9c4] before:content-['·']">발주계획 {tabs.orderPlans}</span>
          </div>
          <div>
            이번 주 마감 {due.week}건 · 가장 빠른 마감{" "}
            {due.soonest ? <><span className={cn("font-[650]", due.soonest.days <= 7 ? "text-orange" : "text-ink")}>D-{due.soonest.days}</span> ({due.soonest.month}.{String(due.soonest.day).padStart(2, "0")})</> : "—"}
          </div>
        </div>
      )}
    </div>
  );
}
