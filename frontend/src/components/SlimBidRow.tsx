import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { daysUntil, formatKRW, scorePercent } from "@/lib/utils";
import type { BidRecommendation } from "@/types/recommendations";

interface Props {
  bid: BidRecommendation;
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
  if (d <= 5) return "text-amber-600 font-semibold";
  return "text-muted-foreground";
}

export function SlimBidRow({ bid, rank }: Props) {
  const d = daysUntil(bid.bid_clse_date);
  const dlabel = ddayLabel(d);
  const instt = bid.dmnd_instt_nm || bid.ntce_instt_nm || "—";
  const price = formatKRW(bid.presmpt_prce);
  const score = scorePercent(bid.score);

  return (
    <Link
      href={`/notices/${bid.bid_ntce_no}`}
      className="group grid grid-cols-[28px_1fr_auto] gap-3 items-center px-3 py-3 rounded-md border border-transparent hover:border-border hover:bg-muted/30 transition-colors"
    >
      <span className="tabular-nums text-[12px] font-bold text-muted-foreground text-right">
        {rank}
      </span>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {bid.bsns_div_nm && (
            <Badge variant="secondary" className="text-[10.5px] font-semibold shrink-0">
              {bid.bsns_div_nm}
            </Badge>
          )}
          <span className="text-[14px] font-semibold text-foreground truncate group-hover:text-primary">
            {bid.bid_ntce_nm}
          </span>
        </div>
        <div className="mt-1 text-[12px] text-muted-foreground truncate">
          {instt}
        </div>
      </div>
      <div className="flex items-center gap-4 text-[12.5px] tabular-nums shrink-0">
        {dlabel && <span className={ddayTone(d)}>{dlabel}</span>}
        <span className="text-foreground/80 w-[60px] text-right">{price}</span>
        <span className="flex flex-col items-end gap-1 w-[40px]">
          <span className="font-bold text-primary leading-none">{score}</span>
          <span className="h-1 w-9 rounded-full bg-muted overflow-hidden" aria-hidden>
            <span
              className="block h-full rounded-full bg-primary"
              style={{ width: `${score}%` }}
            />
          </span>
        </span>
      </div>
    </Link>
  );
}
