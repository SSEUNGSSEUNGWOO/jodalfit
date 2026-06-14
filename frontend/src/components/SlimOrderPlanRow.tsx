import { Badge } from "@/components/ui/badge";
import { formatKRW, scorePercent } from "@/lib/utils";
import type { OrderPlanRecommendation } from "@/types/recommendations";

interface Props {
  plan: OrderPlanRecommendation;
  rank: number;
}

function ymLabel(year: string | null, month: string | null) {
  if (!year && !month) return null;
  const y = year || "—";
  const m = month ? month.padStart(2, "0") : "—";
  return `${y}.${m}`;
}

export function SlimOrderPlanRow({ plan, rank }: Props) {
  const title = plan.biz_nm || plan.prdct_clsfc_no_nm || "—";
  const instt = plan.totlmng_instt_nm || plan.order_instt_nm || "—";
  const price = formatKRW(plan.sum_order_amt);
  const score = scorePercent(plan.score);
  const ym = ymLabel(plan.order_year, plan.order_mnth);

  return (
    <div className="grid grid-cols-[28px_1fr_auto] gap-3 items-center px-3 py-3 rounded-md">
      <span className="tabular-nums text-[12px] font-bold text-muted-foreground text-right">
        {rank}
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {plan.bsns_div_nm && (
            <Badge variant="secondary" className="text-[10.5px] font-semibold shrink-0">
              {plan.bsns_div_nm}
            </Badge>
          )}
          <span className="text-[14px] font-semibold text-foreground truncate">
            {title}
          </span>
        </div>
        <div className="mt-1 text-[12px] text-muted-foreground truncate">{instt}</div>
      </div>
      <div className="flex items-center gap-4 text-[12.5px] tabular-nums shrink-0">
        {ym && (
          <span className="text-muted-foreground" title="발주 예정">
            {ym}
          </span>
        )}
        <span className="text-foreground/80 w-[60px] text-right">{price}</span>
        <span className="font-bold text-muted-foreground w-[40px] text-right">{score}</span>
      </div>
    </div>
  );
}
