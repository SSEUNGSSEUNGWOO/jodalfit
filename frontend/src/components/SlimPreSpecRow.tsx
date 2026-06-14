import { Badge } from "@/components/ui/badge";
import { daysUntil, formatKRW, scorePercent } from "@/lib/utils";
import type { PreSpecRecommendation } from "@/types/recommendations";

interface Props {
  spec: PreSpecRecommendation;
  rank: number;
}

function ddayLabel(d: number | null) {
  if (d == null) return null;
  if (d < 0) return "마감";
  if (d === 0) return "D-Day";
  return `D-${d}`;
}

function ddayTone(d: number | null) {
  if (d == null) return "text-muted-foreground";
  if (d <= 2) return "text-red-600 font-bold";
  if (d <= 5) return "text-amber-700 font-semibold";
  return "text-amber-600";
}

export function SlimPreSpecRow({ spec, rank }: Props) {
  const d = daysUntil(spec.opnin_rgst_clse_dt);
  const dlabel = ddayLabel(d);
  const title = spec.prdct_clsfc_no_nm || spec.prdct_dtl_list || "—";
  const instt = spec.rl_dminstt_nm || spec.order_instt_nm || "—";
  const price = formatKRW(spec.asign_bdgt_amt);
  const score = scorePercent(spec.score);

  return (
    <div className="grid grid-cols-[28px_1fr_auto] gap-3 items-center px-3 py-3 rounded-md">
      <span className="tabular-nums text-[12px] font-bold text-amber-700 text-right">
        {rank}
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {spec.sw_biz_obj_yn === "Y" && (
            <Badge
              variant="outline"
              className="text-[10.5px] font-semibold shrink-0 border-amber-400 text-amber-800 bg-amber-50"
            >
              SW
            </Badge>
          )}
          <span className="text-[14px] font-semibold text-foreground truncate">
            {title}
          </span>
        </div>
        <div className="mt-1 text-[12px] text-muted-foreground truncate">{instt}</div>
      </div>
      <div className="flex items-center gap-4 text-[12.5px] tabular-nums shrink-0">
        {dlabel && (
          <span className={ddayTone(d)} title="의견 마감일">
            {dlabel}
          </span>
        )}
        <span className="text-foreground/80 w-[60px] text-right">{price}</span>
        <span className="font-bold text-amber-700 w-[40px] text-right">{score}</span>
      </div>
    </div>
  );
}
