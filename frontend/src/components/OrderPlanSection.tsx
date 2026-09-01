import { SlimOrderPlanRow } from "@/components/SlimOrderPlanRow";
import type { OrderPlanRecommendation } from "@/types/recommendations";

interface Props {
  results: OrderPlanRecommendation[];
  limit?: number;
}

export function OrderPlanSection({ results, limit = 5 }: Props) {
  if (results.length === 0) return null;
  const top = results.slice(0, limit);
  return (
    <section className="mt-10">
      <div className="flex items-baseline justify-between mb-2 px-1">
        <h3 className="text-[15.5px] sm:text-[16px] font-extrabold tracking-tight text-foreground">
          발주계획 단계 · 선행지표
          <span className="ml-2 text-[12px] font-medium text-muted-foreground">
            {top.length}건
          </span>
        </h3>
        <span className="text-[11.5px] text-muted-foreground font-medium">
          발주 예정 / 예산 / 유사도
        </span>
      </div>
      <p className="px-1 mb-3 text-[12px] text-muted-foreground break-keep">
        아직 사양이 확정되지 않은 발주계획이에요. 본 공고가 나오기 1~3개월 전부터 준비할 수 있는 정보로 활용해 보세요.
      </p>
      <div className="rounded-lg border border-border bg-card overflow-hidden divide-y divide-border">
        {top.map((plan, i) => (
          <SlimOrderPlanRow
            key={`plan-${plan.order_plan_unty_no}`}
            plan={plan}
            rank={i + 1}
          />
        ))}
      </div>
    </section>
  );
}
