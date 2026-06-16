import { Sparkles } from "lucide-react";
import { SlimPreSpecRow } from "@/components/SlimPreSpecRow";
import { daysUntil } from "@/lib/utils";
import type { PreSpecRecommendation } from "@/types/recommendations";

interface Props {
  results: PreSpecRecommendation[];
  limit?: number;
}

export function PreSpecSection({ results, limit = 5 }: Props) {
  if (results.length === 0) return null;
  // 마감 임박(D-0~D-2) 우선, 그 안에서 점수 내림차순. 마감일 미상은 맨 뒤.
  const sorted = [...results].sort((a, b) => {
    const da = daysUntil(a.opnin_rgst_clse_dt);
    const db = daysUntil(b.opnin_rgst_clse_dt);
    const ac = da !== null && da >= 0 && da <= 2 ? 1 : 0;
    const bc = db !== null && db >= 0 && db <= 2 ? 1 : 0;
    if (ac !== bc) return bc - ac;
    return (b.score ?? 0) - (a.score ?? 0);
  });
  const top = sorted.slice(0, limit);
  const closingCount = top.filter((s) => {
    const d = daysUntil(s.opnin_rgst_clse_dt);
    return d !== null && d >= 0 && d <= 2;
  }).length;

  return (
    <section className="mt-10 rounded-2xl border-2 border-amber-400 bg-amber-50/60 p-5 sm:p-7">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-500 text-white">
            <Sparkles className="h-3.5 w-3.5" strokeWidth={2.5} />
          </span>
          <h2 className="text-[20px] sm:text-[24px] font-extrabold text-amber-950 tracking-tight">
            지금 의견 낼 수 있는 공고 {top.length}건
          </h2>
        </div>
        <span className="text-[12px] text-amber-800 font-semibold">
          사전규격 단계 · 의견 등록으로 사양 반영 가능
        </span>
      </div>
      <p className="text-[13.5px] text-amber-900/80 mb-4 leading-relaxed break-keep">
        입찰공고가 뜨면 사양이 굳어져 변경이 어려워요. 지금이 사양에 의견을 낼 수 있는 마지막 타이밍이에요.
        {closingCount > 0 && (
          <>
            {" "}
            <span className="font-bold text-red-700">{closingCount}건</span>은 D-2 이내라 가장 급해요.
          </>
        )}
      </p>
      <div className="rounded-lg bg-white border border-amber-200 overflow-hidden divide-y divide-amber-100">
        {top.map((spec, i) => (
          <SlimPreSpecRow
            key={`prespec-${spec.bf_spec_rgst_no}`}
            spec={spec}
            rank={i + 1}
          />
        ))}
      </div>
    </section>
  );
}
