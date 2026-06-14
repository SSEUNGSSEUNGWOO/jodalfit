import { SlimPreSpecRow } from "@/components/SlimPreSpecRow";
import type { PreSpecRecommendation } from "@/types/recommendations";

interface Props {
  results: PreSpecRecommendation[];
  limit?: number;
}

export function PreSpecSection({ results, limit = 5 }: Props) {
  if (results.length === 0) return null;
  const top = results.slice(0, limit);
  return (
    <section className="mt-10 rounded-xl border border-amber-200 bg-amber-50/40 p-4 sm:p-5">
      <div className="flex items-baseline justify-between mb-2 px-1">
        <h3 className="text-[15.5px] sm:text-[16px] font-extrabold tracking-tight text-amber-900">
          사전규격 단계 · 골든타임
          <span className="ml-2 text-[12px] font-medium text-amber-700">
            {top.length}건
          </span>
        </h3>
        <span className="text-[11.5px] text-amber-700 font-medium">
          의견 마감 / 예산 / 유사도
        </span>
      </div>
      <p className="px-1 mb-3 text-[12px] text-amber-800/80 break-keep">
        본공고 전 사양에 의견을 낼 수 있는 시점입니다. 의견 마감일을 우선 확인하세요.
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
